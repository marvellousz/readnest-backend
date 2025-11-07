from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from supabase_config import supabase, TABLES
from pydantic import BaseModel

# Pydantic models for database operations
class JournalEntry(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    word_count: int
    keywords: Optional[Dict[str, int]] = {}
    user_id: Optional[str] = None

class FeedSubscription(BaseModel):
    id: str
    url: str
    title: str
    description: str
    last_updated: str
    is_active: bool = True
    user_id: Optional[str] = None

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
    user_id: Optional[str] = None

class Document(BaseModel):
    id: str
    name: str
    type: str  # 'pdf' or 'doc'
    size: int
    upload_date: str
    content: Optional[str] = None
    status: str = "ready"  # 'uploading', 'processing', 'ready', 'error'
    user_id: Optional[str] = None

class DatabaseService:
    """Service class to handle all database operations with Supabase"""
    
    def __init__(self):
        self.supabase = supabase
    
    # Journal operations
    def get_all_journals(self, user_id: Optional[str] = None) -> List[JournalEntry]:
        """Get all journal entries, optionally filtered by user_id"""
        try:
            query = self.supabase.table(TABLES['journals']).select("*")
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.order('updated_at', desc=True).execute()
            return [JournalEntry(**journal) for journal in result.data]
        except Exception as e:
            print(f"Error fetching journals: {e}")
            return []
    
    def get_journal(self, journal_id: str) -> Optional[JournalEntry]:
        """Get a specific journal entry by ID"""
        try:
            result = self.supabase.table(TABLES['journals']).select("*").eq('id', journal_id).execute()
            if result.data:
                return JournalEntry(**result.data[0])
            return None
        except Exception as e:
            print(f"Error fetching journal {journal_id}: {e}")
            return None
    
    def create_journal(self, journal_data: Dict[str, Any]) -> Optional[JournalEntry]:
        """Create a new journal entry"""
        try:
            journal_id = f"j_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            now = datetime.now().isoformat()
            
            journal_entry = {
                'id': journal_id,
                'title': journal_data.get('title', ''),
                'content': journal_data.get('content', ''),
                'created_at': now,
                'updated_at': now,
                'word_count': len(journal_data.get('content', '').split()),
                'keywords': journal_data.get('keywords', {}),
                'user_id': journal_data.get('user_id')
            }
            
            result = self.supabase.table(TABLES['journals']).insert(journal_entry).execute()
            if result.data:
                return JournalEntry(**result.data[0])
            return None
        except Exception as e:
            print(f"Error creating journal: {e}")
            return None
    
    def update_journal(self, journal_id: str, journal_data: Dict[str, Any]) -> Optional[JournalEntry]:
        """Update an existing journal entry"""
        try:
            update_data = {
                'updated_at': datetime.now().isoformat(),
                'word_count': len(journal_data.get('content', '').split()),
                'keywords': journal_data.get('keywords', {})
            }
            
            # Add provided fields
            if 'title' in journal_data:
                update_data['title'] = journal_data['title']
            if 'content' in journal_data:
                update_data['content'] = journal_data['content']
            
            result = self.supabase.table(TABLES['journals']).update(update_data).eq('id', journal_id).execute()
            if result.data:
                return JournalEntry(**result.data[0])
            return None
        except Exception as e:
            print(f"Error updating journal {journal_id}: {e}")
            return None
    
    def delete_journal(self, journal_id: str) -> bool:
        """Delete a journal entry"""
        try:
            result = self.supabase.table(TABLES['journals']).delete().eq('id', journal_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting journal {journal_id}: {e}")
            return False
    
    def search_journals(self, query: str, user_id: Optional[str] = None) -> List[JournalEntry]:
        """Search journals by title, content, or keywords"""
        try:
            # Use PostgreSQL full-text search
            search_query = self.supabase.table(TABLES['journals']).select("*")
            
            if user_id:
                search_query = search_query.eq('user_id', user_id)
            
            # Search in title and content using ilike (case-insensitive)
            result = search_query.or_(f"title.ilike.%{query}%,content.ilike.%{query}%").execute()
            return [JournalEntry(**journal) for journal in result.data]
        except Exception as e:
            print(f"Error searching journals: {e}")
            return []
    
    # Feed operations
    def get_all_feed_subscriptions(self, user_id: Optional[str] = None) -> List[FeedSubscription]:
        """Get all feed subscriptions"""
        try:
            query = self.supabase.table(TABLES['feed_subscriptions']).select("*")
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.execute()
            return [FeedSubscription(**feed) for feed in result.data]
        except Exception as e:
            print(f"Error fetching feed subscriptions: {e}")
            return []
    
    def create_feed_subscription(self, feed_data: Dict[str, Any]) -> Optional[FeedSubscription]:
        """Create a new feed subscription"""
        try:
            feed_id = f"feed_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            now = datetime.now().isoformat()
            
            subscription = {
                'id': feed_id,
                'url': feed_data.get('url', ''),
                'title': feed_data.get('title', ''),
                'description': feed_data.get('description', ''),
                'last_updated': now,
                'is_active': feed_data.get('is_active', True),
                'user_id': feed_data.get('user_id')
            }
            
            result = self.supabase.table(TABLES['feed_subscriptions']).insert(subscription).execute()
            if result.data:
                return FeedSubscription(**result.data[0])
            return None
        except Exception as e:
            print(f"Error creating feed subscription: {e}")
            return None
    
    def delete_feed_subscription(self, subscription_id: str) -> bool:
        """Delete a feed subscription"""
        try:
            result = self.supabase.table(TABLES['feed_subscriptions']).delete().eq('id', subscription_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting feed subscription {subscription_id}: {e}")
            return False
    
    # Article operations
    def get_all_articles(self, user_id: Optional[str] = None) -> List[Article]:
        """Get all articles"""
        try:
            query = self.supabase.table(TABLES['articles']).select("*")
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.order('date', desc=True).execute()
            return [Article(**article) for article in result.data]
        except Exception as e:
            print(f"Error fetching articles: {e}")
            return []
    
    def create_article(self, article_data: Dict[str, Any]) -> Optional[Article]:
        """Create a new article"""
        try:
            article_id = f"article_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            article = {
                'id': article_id,
                'title': article_data.get('title', ''),
                'source': article_data.get('source', ''),
                'snippet': article_data.get('snippet', ''),
                'date': article_data.get('date', datetime.now().isoformat().split('T')[0]),
                'type': article_data.get('type', 'rss'),
                'url': article_data.get('url'),
                'feed_id': article_data.get('feed_id'),
                'content': article_data.get('content'),
                'author': article_data.get('author'),
                'tags': article_data.get('tags', []),
                'user_id': article_data.get('user_id')
            }
            
            result = self.supabase.table(TABLES['articles']).insert(article).execute()
            if result.data:
                return Article(**result.data[0])
            return None
        except Exception as e:
            print(f"Error creating article: {e}")
            return None
    
    # Document operations
    def get_all_documents(self, user_id: Optional[str] = None) -> List[Document]:
        """Get all documents"""
        try:
            query = self.supabase.table(TABLES['documents']).select("*")
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.order('upload_date', desc=True).execute()
            return [Document(**doc) for doc in result.data]
        except Exception as e:
            print(f"Error fetching documents: {e}")
            return []
    
    def create_document(self, document_data: Dict[str, Any]) -> Optional[Document]:
        """Create a new document"""
        try:
            doc_id = f"doc_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            now = datetime.now().isoformat()
            
            document = {
                'id': doc_id,
                'name': document_data.get('name', ''),
                'type': document_data.get('type', ''),
                'size': document_data.get('size', 0),
                'upload_date': now,
                'content': document_data.get('content'),
                'status': document_data.get('status', 'ready'),
                'user_id': document_data.get('user_id')
            }
            
            result = self.supabase.table(TABLES['documents']).insert(document).execute()
            if result.data:
                return Document(**result.data[0])
            return None
        except Exception as e:
            print(f"Error creating document: {e}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        try:
            result = self.supabase.table(TABLES['documents']).delete().eq('id', document_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting document {document_id}: {e}")
            return False

# Global database service instance
db_service = DatabaseService()




