from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from scholar_agent import scholar_agent
import json
import os
from datetime import datetime
import uuid
import feedparser
import requests
from bs4 import BeautifulSoup
import PyPDF2
import docx
import io
import httpx
import traceback, json

app = FastAPI(title="ReadNest Backend", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class JournalEntry(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    word_count: int
    keywords: Optional[dict] = {}

class JournalCreate(BaseModel):
    title: str
    content: str = ""

class JournalUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# In-memory storage (replace with database later)
JOURNALS_FILE = "journals.json"

def load_journals() -> List[JournalEntry]:
    """Load journals from local JSON file"""
    if os.path.exists(JOURNALS_FILE):
        try:
            with open(JOURNALS_FILE, 'r') as f:
                data = json.load(f)
                return [JournalEntry(**entry) for entry in data]
        except Exception:
            return []
    return []

def save_journals(journals: List[JournalEntry]):
    """Save journals to local JSON file"""
    with open(JOURNALS_FILE, 'w') as f:
        json.dump([journal.dict() for journal in journals], f, indent=2)

def extract_keywords(text: str, top_n: int = 30) -> dict:
    """Extract keywords from text"""
    if not text:
        return {}
    
    import re
    # Simple tokenization and frequency counting
    tokens = re.sub(r'[^\w\s]', ' ', text.lower()).split()
    tokens = [t for t in tokens if len(t) > 2]  # Filter short words
    
    freq = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    
    # Return top N keywords
    sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return dict(sorted_keywords)

@app.get("/")
def read_root():
    return {"message": "ReadNest Backend API", "version": "1.0.0"}

# Journal API endpoints
@app.get("/api/journals", response_model=List[JournalEntry])
def get_all_journals():
    """Get all journal entries"""
    journals = load_journals()
    # Sort by updated_at descending
    journals.sort(key=lambda x: x.updated_at, reverse=True)
    return journals

@app.get("/api/journals/{journal_id}", response_model=JournalEntry)
def get_journal(journal_id: str):
    """Get a specific journal entry"""
    journals = load_journals()
    journal = next((j for j in journals if j.id == journal_id), None)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal

@app.post("/api/journals", response_model=JournalEntry)
def create_journal(journal_data: JournalCreate):
    """Create a new journal entry"""
    now = datetime.now().isoformat()
    journal_id = f"j_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    
    # Calculate word count and extract keywords
    word_count = len(journal_data.content.split()) if journal_data.content else 0
    keywords = extract_keywords(journal_data.content)
    
    new_journal = JournalEntry(
        id=journal_id,
        title=journal_data.title,
        content=journal_data.content,
        created_at=now,
        updated_at=now,
        word_count=word_count,
        keywords=keywords
    )
    
    journals = load_journals()
    journals.append(new_journal)
    save_journals(journals)
    
    return new_journal

@app.put("/api/journals/{journal_id}", response_model=JournalEntry)
def update_journal(journal_id: str, journal_data: JournalUpdate):
    """Update an existing journal entry"""
    journals = load_journals()
    journal = next((j for j in journals if j.id == journal_id), None)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    
    # Update fields if provided
    if journal_data.title is not None:
        journal.title = journal_data.title
    if journal_data.content is not None:
        journal.content = journal_data.content
    
    # Update metadata
    journal.updated_at = datetime.now().isoformat()
    journal.word_count = len(journal.content.split()) if journal.content else 0
    journal.keywords = extract_keywords(journal.content)
    
    save_journals(journals)
    return journal

@app.delete("/api/journals/{journal_id}")
def delete_journal(journal_id: str):
    """Delete a journal entry"""
    journals = load_journals()
    journal = next((j for j in journals if j.id == journal_id), None)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    
    journals = [j for j in journals if j.id != journal_id]
    save_journals(journals)
    
    return {"message": "Journal deleted successfully"}

@app.get("/api/journals/search/{query}")
def search_journals(query: str):
    """Search journals by title or content"""
    journals = load_journals()
    query_lower = query.lower()
    
    matching_journals = []
    for journal in journals:
        if (query_lower in journal.title.lower() or 
            query_lower in journal.content.lower() or
            any(query_lower in keyword.lower() for keyword in journal.keywords.keys())):
            matching_journals.append(journal)
    
    return matching_journals

# RSS Feed System

class FeedSubscription(BaseModel):
    id: str
    url: str
    title: str
    description: str
    last_updated: str
    is_active: bool = True

class Article(BaseModel):
    id: str
    title: str
    source: str
    snippet: str
    date: str
    type: str  # 'rss' or 'pdf'
    url: Optional[str] = None
    feed_id: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = []

class FeedCreate(BaseModel):
    url: str
    name: str

class Document(BaseModel):
    id: str
    name: str
    type: str  # 'pdf' or 'doc'
    size: int
    upload_date: str
    content: Optional[str] = None
    status: str = "ready"  # 'uploading', 'processing', 'ready', 'error'

# Storage files
FEEDS_FILE = "feed_subscriptions.json"
ARTICLES_FILE = "articles.json"
DOCUMENTS_FILE = "documents.json"

def load_feed_subscriptions() -> List[FeedSubscription]:
    """Load feed subscriptions from local JSON file"""
    if os.path.exists(FEEDS_FILE):
        try:
            with open(FEEDS_FILE, 'r') as f:
                data = json.load(f)
                return [FeedSubscription(**feed) for feed in data]
        except Exception:
            return []
    return []

def save_feed_subscriptions(subscriptions: List[FeedSubscription]):
    """Save feed subscriptions to local JSON file"""
    with open(FEEDS_FILE, 'w') as f:
        json.dump([sub.dict() for sub in subscriptions], f, indent=2)

def load_articles() -> List[Article]:
    """Load articles from local JSON file"""
    if os.path.exists(ARTICLES_FILE):
        try:
            with open(ARTICLES_FILE, 'r') as f:
                data = json.load(f)
                return [Article(**article) for article in data]
        except Exception:
            return []
    return []

def save_articles(articles: List[Article]):
    """Save articles to local JSON file"""
    with open(ARTICLES_FILE, 'w') as f:
        json.dump([article.dict() for article in articles], f, indent=2)

def load_documents() -> List[Document]:
    """Load documents from local JSON file"""
    if os.path.exists(DOCUMENTS_FILE):
        try:
            with open(DOCUMENTS_FILE, 'r') as f:
                data = json.load(f)
                return [Document(**doc) for doc in data]
        except Exception:
            return []
    return []

def save_documents(documents: List[Document]):
    """Save documents to local JSON file"""
    with open(DOCUMENTS_FILE, 'w') as f:
        json.dump([doc.dict() for doc in documents], f, indent=2)

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(io.BytesIO(file_content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {str(e)}")

def process_document(file: UploadFile) -> Document:
    """Process uploaded document and extract text"""
    # Read file content
    file_content = file.file.read()
    
    # Determine file type
    file_type = "pdf" if file.content_type == "application/pdf" else "doc"
    
    # Extract text based on file type
    try:
        if file_type == "pdf":
            content = extract_text_from_pdf(file_content)
        else:  # docx
            content = extract_text_from_docx(file_content)
    except Exception as e:
        raise Exception(f"Failed to process document: {str(e)}")
    
    # Create document object
    document = Document(
        id=f"doc_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",
        name=file.filename,
        type=file_type,
        size=len(file_content),
        upload_date=datetime.now().isoformat(),
        content=content,
        status="ready"
    )
    
    return document

def parse_rss_feed(feed_url: str, custom_name: str = None) -> tuple[FeedSubscription, List[Article]]:
    """Parse RSS feed and return subscription info and articles"""
    try:
        # Parse the RSS feed
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            raise Exception(f"Invalid RSS feed: {feed.bozo_exception}")
        
        if not feed.entries:
            raise Exception("No entries found in RSS feed")
        
        # Create feed subscription
        subscription = FeedSubscription(
            id=f"feed_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",
            url=feed_url,
            title=custom_name or feed.feed.get('title', 'Untitled Feed'),
            description=feed.feed.get('description', 'No description'),
            last_updated=datetime.now().isoformat(),
            is_active=True
        )
        
        # Parse articles
        articles = []
        for entry in feed.entries[:50]:  # Limit to 50 most recent articles
            # Extract content
            content = ""
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if entry.content else ""
            elif hasattr(entry, 'summary'):
                content = entry.summary
            
            # Clean HTML content
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text()[:1000]  # Limit to 1000 chars
            
            # Extract snippet
            snippet = content[:200] + "..." if len(content) > 200 else content
            if not snippet and hasattr(entry, 'summary'):
                snippet = entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary
            
            # Parse date
            article_date = datetime.now().isoformat().split('T')[0]  # Default to today
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    article_date = datetime(*entry.published_parsed[:6]).isoformat().split('T')[0]
                except:
                    pass
            
            # Extract tags properly
            tags = []
            if hasattr(entry, 'tags') and entry.tags:
                for tag in entry.tags[:5]:  # Limit to 5 tags
                    if hasattr(tag, 'term') and tag.term:
                        tags.append(tag.term)
                    elif isinstance(tag, str):
                        tags.append(tag)
            
            article = Article(
                id=f"article_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}",
                title=entry.get('title', 'Untitled Article'),
                source=subscription.title,
                snippet=snippet,
                date=article_date,
                type="rss",
                url=entry.get('link', ''),
                feed_id=subscription.id,
                content=content,
                author=entry.get('author', ''),
                tags=tags
            )
            articles.append(article)
        
        return subscription, articles
        
    except Exception as e:
        raise Exception(f"Failed to parse RSS feed: {str(e)}")

def refresh_all_feeds():
    """Refresh all active feed subscriptions"""
    subscriptions = load_feed_subscriptions()
    all_articles = load_articles()
    
    for subscription in subscriptions:
        if not subscription.is_active:
            continue
            
        try:
            _, new_articles = parse_rss_feed(subscription.url)
            
            # Update subscription
            subscription.last_updated = datetime.now().isoformat()
            
            # Add new articles (avoid duplicates)
            existing_urls = {article.url for article in all_articles if article.url}
            for article in new_articles:
                if article.url not in existing_urls:
                    all_articles.append(article)
            
        except Exception as e:
            print(f"Failed to refresh feed {subscription.title}: {e}")
    
    # Save updated data
    save_feed_subscriptions(subscriptions)
    save_articles(all_articles)
    
    return all_articles

# Feed API endpoints
@app.get("/api/feeds", response_model=List[Article])
def get_all_articles():
    """Get all articles from active feeds only"""
    articles = load_articles()
    subscriptions = load_feed_subscriptions()
    
    # Get list of active feed IDs
    active_feed_ids = {sub.id for sub in subscriptions if sub.is_active}
    
    # Filter articles to only include those from active feeds
    active_articles = [article for article in articles if article.feed_id in active_feed_ids]
    
    # Sort by date descending
    active_articles.sort(key=lambda x: x.date, reverse=True)
    return active_articles

@app.get("/api/feeds/subscriptions", response_model=List[FeedSubscription])
def get_feed_subscriptions():
    """Get all feed subscriptions"""
    return load_feed_subscriptions()

@app.post("/api/feeds", response_model=dict)
def add_feed_subscription(feed_data: FeedCreate):
    """Add a new RSS feed subscription"""
    try:
        # Parse the RSS feed
        subscription, articles = parse_rss_feed(feed_data.url, feed_data.name)
        
        # Check if feed already exists
        existing_subscriptions = load_feed_subscriptions()
        for existing in existing_subscriptions:
            if existing.url == feed_data.url:
                raise HTTPException(status_code=400, detail="Feed already exists")
        
        # Save subscription
        existing_subscriptions.append(subscription)
        save_feed_subscriptions(existing_subscriptions)
        
        # Save articles
        existing_articles = load_articles()
        existing_articles.extend(articles)
        save_articles(existing_articles)
        
        return {
            "message": "Feed added successfully",
            "subscription": subscription,
            "articles_count": len(articles)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/feeds/subscriptions/{subscription_id}")
def delete_feed_subscription(subscription_id: str):
    """Delete a feed subscription and its articles"""
    subscriptions = load_feed_subscriptions()
    subscription = next((s for s in subscriptions if s.id == subscription_id), None)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Feed subscription not found")
    
    # Remove subscription
    subscriptions = [s for s in subscriptions if s.id != subscription_id]
    save_feed_subscriptions(subscriptions)
    
    # Remove articles from this feed
    articles = load_articles()
    articles = [a for a in articles if a.feed_id != subscription_id]
    save_articles(articles)
    
    return {"message": "Feed subscription deleted successfully"}

@app.post("/api/feeds/subscriptions/{subscription_id}/toggle")
def toggle_feed_subscription(subscription_id: str, toggle_data: dict):
    """Toggle feed subscription active status"""
    subscriptions = load_feed_subscriptions()
    subscription = next((s for s in subscriptions if s.id == subscription_id), None)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Feed subscription not found")
    
    # Update subscription status
    subscription.is_active = toggle_data.get('is_active', not subscription.is_active)
    
    # Save updated subscriptions
    save_feed_subscriptions(subscriptions)
    
    return {
        "message": f"Feed subscription {'activated' if subscription.is_active else 'deactivated'} successfully",
        "is_active": subscription.is_active
    }

@app.post("/api/feeds/refresh")
def refresh_feeds():
    """Manually refresh all feeds"""
    try:
        articles = refresh_all_feeds()
        return {
            "message": "Feeds refreshed successfully",
            "total_articles": len(articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh feeds: {str(e)}")

@app.get("/api/feeds/search/{query}")
def search_articles(query: str):
    """Search articles by title, content, or tags"""
    articles = load_articles()
    query_lower = query.lower()
    
    matching_articles = []
    for article in articles:
        if (query_lower in article.title.lower() or 
            query_lower in article.snippet.lower() or
            query_lower in (article.content or "").lower() or
            any(query_lower in tag.lower() for tag in (article.tags or []))):
            matching_articles.append(article)
    
    return matching_articles

# Document API endpoints
@app.get("/api/documents", response_model=List[Document])
def get_all_documents():
    """Get all uploaded documents"""
    documents = load_documents()
    # Sort by upload_date descending
    documents.sort(key=lambda x: x.upload_date, reverse=True)
    return documents

@app.get("/api/documents/{document_id}", response_model=Document)
def get_document(document_id: str):
    """Get a specific document"""
    documents = load_documents()
    document = next((d for d in documents if d.id == document_id), None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@app.post("/api/documents/upload", response_model=Document)
def upload_document(file: UploadFile = File(...), name: str = Form(...)):
    """Upload and process a document"""
    # Validate file type
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    # Validate file size (10MB limit)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        # Process the document
        document = process_document(file)
        
        # Save to storage
        documents = load_documents()
        documents.append(document)
        save_documents(documents)
        
        return document
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    """Delete a document"""
    documents = load_documents()
    document = next((d for d in documents if d.id == document_id), None)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove document
    documents = [d for d in documents if d.id != document_id]
    save_documents(documents)
    
    return {"message": "Document deleted successfully"}

@app.get("/api/documents/search/{query}")
def search_documents(query: str):
    """Search documents by name or content"""
    documents = load_documents()
    query_lower = query.lower()
    
    matching_documents = []
    for document in documents:
        if (query_lower in document.name.lower() or 
            query_lower in (document.content or "").lower()):
            matching_documents.append(document)
    
    return matching_documents

@app.get("/api/search")
async def search_papers(q: str = Query(...), top_k: int = 5, source: str = "semantic_scholar"):
    """
    Search for papers using multiple academic APIs.
    Sources: semantic_scholar, openalex, arxiv, pubmed
    """
    results = []
    
    if source == "semantic_scholar" or source == "all":
        # Semantic Scholar API
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit={top_k}&fields=title,url,abstract"
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    for paper in data.get("data", []):
                        abstract = paper.get("abstract") or ""
                        title = paper.get("title") or "Untitled"
                        link = paper.get("url") or ""
                        results.append({
                            "title": title,
                            "summary": abstract[:500],
                            "link": link,
                            "source": "Semantic Scholar"
                        })
        except Exception as e:
            print(f"Semantic Scholar error: {e}")
    
    if source == "openalex" or source == "all":
        # OpenAlex API - following their best practices
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(q)
            # Use proper email for polite pool and better rate limits
            url = f"https://api.openalex.org/works?search={encoded_query}&per_page={top_k}&mailto=readnest@example.com"
            print(f"OpenAlex URL: {url}")
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                print(f"OpenAlex response status: {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    print(f"OpenAlex found {len(data.get('results', []))} results")
                    for work in data.get("results", []):
                        # Extract abstract - OpenAlex uses abstract_inverted_index format
                        abstract_text = ""
                        if work.get("abstract_inverted_index"):
                            # Convert inverted index to readable text
                            abstract = work["abstract_inverted_index"]
                            words = []
                            for word, positions in abstract.items():
                                for pos in positions:
                                    words.append((pos, word))
                            words.sort()
                            abstract_text = " ".join([word for pos, word in words])
                        elif work.get("abstract"):
                            # Fallback to direct abstract if available
                            abstract_text = work["abstract"]
                        
                        title = work.get("title", "Untitled")
                        
                        # Get best available link following OpenAlex priority
                        link = ""
                        if work.get("open_access", {}).get("oa_url"):
                            # Open access PDF link (best option)
                            link = work["open_access"]["oa_url"]
                        elif work.get("primary_location", {}).get("landing_page_url"):
                            # Publisher landing page
                            link = work["primary_location"]["landing_page_url"]
                        elif work.get("doi"):
                            # DOI link
                            link = f"https://doi.org/{work['doi']}"
                        elif work.get("id"):
                            # OpenAlex page as fallback
                            link = work["id"]
                        
                        # Get publication year and venue information
                        pub_year = work.get("publication_year", "")
                        venue = work.get("primary_location", {}).get("source", {}).get("display_name", "")
                        
                        # Create enhanced title with year and venue
                        title_parts = [title]
                        if pub_year:
                            title_parts.append(f"({pub_year})")
                        if venue:
                            title_parts.append(f"- {venue}")
                        
                        enhanced_title = " ".join(title_parts)
                        
                        results.append({
                            "title": enhanced_title,
                            "summary": abstract_text[:500] if abstract_text else "No abstract available",
                            "link": link,
                            "source": "OpenAlex"
                        })
                else:
                    print(f"OpenAlex error: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"OpenAlex error: {e}")
            import traceback
            traceback.print_exc()
    
    if source == "arxiv" or source == "all":
        # arXiv API (no key required) - using correct URL format
        try:
            # Use HTTPS and proper URL encoding for arXiv API
            import urllib.parse
            encoded_query = urllib.parse.quote(f"all:{q}")
            url = f"https://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={top_k}&sortBy=relevance&sortOrder=descending"
            print(f"arXiv URL: {url}")
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                print(f"arXiv response status: {r.status_code}")
                if r.status_code == 200:
                    # Parse XML response using the correct namespace
                    from xml.etree import ElementTree as ET
                    root = ET.fromstring(r.text)
                    
                    # Find all entries using the correct namespace
                    entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    print(f"arXiv found {len(entries)} results")
                    
                    for entry in entries:
                        # Extract title
                        title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title')
                        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled"
                        
                        # Extract summary/abstract
                        summary_elem = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                        summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "No abstract available"
                        
                        # Extract arXiv ID and create proper link
                        id_elem = entry.find('.//{http://www.w3.org/2005/Atom}id')
                        arxiv_id = ""
                        if id_elem is not None and id_elem.text:
                            # Extract arXiv ID from URL like "http://arxiv.org/abs/hep-ex/0307015"
                            arxiv_id = id_elem.text.split('/')[-1]
                        
                        # Create proper arXiv link
                        link = f"http://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
                        
                        # Get publication date
                        published_elem = entry.find('.//{http://www.w3.org/2005/Atom}published')
                        pub_date = ""
                        if published_elem is not None and published_elem.text:
                            pub_date = published_elem.text[:4]  # Extract year
                        year_suffix = f" ({pub_date})" if pub_date else ""
                        
                        # Get authors
                        authors = []
                        for author in entry.findall('.//{http://www.w3.org/2005/Atom}author'):
                            name_elem = author.find('.//{http://www.w3.org/2005/Atom}name')
                            if name_elem is not None and name_elem.text:
                                authors.append(name_elem.text.strip())
                        
                        author_text = f" by {', '.join(authors[:3])}" if authors else ""
                        if len(authors) > 3:
                            author_text += f" et al."
                        
                        results.append({
                            "title": title + year_suffix + author_text,
                            "summary": summary[:500],
                            "link": link,
                            "source": "arXiv"
                        })
                else:
                    print(f"arXiv error: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"arXiv error: {e}")
            import traceback
            traceback.print_exc()
    
    if source == "pubmed" or source == "all":
        # PubMed API (no key required for basic search)
        try:
            # First search for PMIDs
            import urllib.parse
            encoded_query = urllib.parse.quote(q)
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmax={top_k}&retmode=json"
            print(f"PubMed search URL: {search_url}")
            async with httpx.AsyncClient() as client:
                r = await client.get(search_url)
                if r.status_code == 200:
                    search_data = r.json()
                    pmids = search_data.get("esearchresult", {}).get("idlist", [])
                    print(f"PubMed found {len(pmids)} PMIDs")
                    
                    if pmids:
                        # Get details for each PMID
                        pmids_str = ",".join(pmids)
                        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmids_str}&retmode=xml"
                        
                        r2 = await client.get(fetch_url)
                        if r2.status_code == 200:
                            # Parse XML response
                            from xml.etree import ElementTree as ET
                            root = ET.fromstring(r2.text)
                            
                            articles = root.findall('.//PubmedArticle')
                            for article in articles:
                                title_elem = article.find('.//ArticleTitle')
                                title = title_elem.text if title_elem is not None else "Untitled"
                                
                                abstract_elem = article.find('.//AbstractText')
                                abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
                                
                                pmid_elem = article.find('.//PMID')
                                pmid = pmid_elem.text if pmid_elem is not None else ""
                                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
                                
                                # Get publication year
                                year_elem = article.find('.//PubDate/Year')
                                pub_year = year_elem.text if year_elem is not None else ""
                                year_suffix = f" ({pub_year})" if pub_year else ""
                                
                                results.append({
                                    "title": title + year_suffix,
                                    "summary": abstract[:500],
                                    "link": link,
                                    "source": "PubMed"
                                })
        except Exception as e:
            print(f"PubMed error: {e}")
            import traceback
            traceback.print_exc()

    return {"results": results}

@app.post("/api/scholar-agent")
async def run_scholar_agent(payload: dict):
    """
    payload: {"user_prompt": "...", "papers": [...]}
    """
    try:
        # invoke the compiled graph
        result = scholar_agent.invoke({
            "user_prompt": payload.get("user_prompt", ""),
            "papers": payload.get("papers", [])
        })

        # result should be a dict with 'results'
        if isinstance(result, dict):
            results = result.get("results", [])
            # return normalized response (include error/raw if present)
            return {"results": results, "error": result.get("error"), "raw": result.get("raw")}
        else:
            # try parse if it's a string (rare)
            try:
                parsed = json.loads(result)
                return {"results": parsed if isinstance(parsed, list) else [], "raw": result}
            except Exception:
                return {"results": [], "raw": str(result)}

    except Exception as e:
        tb = traceback.format_exc()
        print("scholar_agent endpoint error:", tb)
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict] = []

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """
    Simple AI chat endpoint using Groq API directly
    """
    try:
        from langchain_groq import ChatGroq
        
        # Initialize Groq client using langchain_groq (same as scholar_agent)
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.7,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )
        
        # Build conversation context
        conversation_context = "You are a helpful AI assistant. You can help with general questions, explanations, creative tasks, and casual conversation. Be friendly, informative, and concise.\n\n"
        
        # Add conversation history (last 10 messages)
        for msg in request.conversation_history[-10:]:
            if msg.get('role') == 'user':
                conversation_context += f"User: {msg['content']}\n"
            elif msg.get('role') == 'assistant':
                conversation_context += f"Assistant: {msg['content']}\n"
        
        # Add current message
        conversation_context += f"User: {request.message}\nAssistant:"
        
        # Get response from Groq
        response = llm.invoke(conversation_context)
        ai_response = response.content
        
        return {"response": ai_response}
        
    except Exception as e:
        tb = traceback.format_exc()
        print("chat endpoint error:", tb)
        raise HTTPException(status_code=500, detail=str(e))
