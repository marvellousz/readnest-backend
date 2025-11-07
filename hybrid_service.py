import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from database_service import db_service, JournalEntry, FeedSubscription, Article, Document

class HybridService:
    """
    Hybrid service that tries Supabase first, falls back to JSON files
    """
    
    def __init__(self):
        self.db_service = db_service
        self.use_database = True
        self.json_files = {
            'journals': 'journals.json',
            'feeds': 'feed_subscriptions.json', 
            'articles': 'articles.json',
            'documents': 'documents.json'
        }
    
    def _try_database_operation(self, operation, fallback_operation):
        """Try database operation, fallback to JSON if it fails"""
        if not self.use_database:
            return fallback_operation()
        
        try:
            return operation()
        except Exception as e:
            print(f"Database operation failed, falling back to JSON: {e}")
            self.use_database = False
            return fallback_operation()
    
    # Journal operations
    def get_all_journals(self, user_id: Optional[str] = None) -> List[JournalEntry]:
        def db_operation():
            return self.db_service.get_all_journals(user_id)
        
        def json_operation():
            return self._load_journals_from_json()
        
        return self._try_database_operation(db_operation, json_operation)
    
    def get_journal(self, journal_id: str) -> Optional[JournalEntry]:
        def db_operation():
            return self.db_service.get_journal(journal_id)
        
        def json_operation():
            journals = self._load_journals_from_json()
            return next((j for j in journals if j.id == journal_id), None)
        
        return self._try_database_operation(db_operation, json_operation)
    
    def create_journal(self, journal_data: Dict[str, Any]) -> Optional[JournalEntry]:
        def db_operation():
            return self.db_service.create_journal(journal_data)
        
        def json_operation():
            return self._create_journal_json(journal_data)
        
        return self._try_database_operation(db_operation, json_operation)
    
    def update_journal(self, journal_id: str, journal_data: Dict[str, Any]) -> Optional[JournalEntry]:
        def db_operation():
            return self.db_service.update_journal(journal_id, journal_data)
        
        def json_operation():
            return self._update_journal_json(journal_id, journal_data)
        
        return self._try_database_operation(db_operation, json_operation)
    
    def delete_journal(self, journal_id: str) -> bool:
        def db_operation():
            return self.db_service.delete_journal(journal_id)
        
        def json_operation():
            return self._delete_journal_json(journal_id)
        
        return self._try_database_operation(db_operation, json_operation)
    
    def search_journals(self, query: str, user_id: Optional[str] = None) -> List[JournalEntry]:
        def db_operation():
            return self.db_service.search_journals(query, user_id)
        
        def json_operation():
            return self._search_journals_json(query)
        
        return self._try_database_operation(db_operation, json_operation)
    
    # JSON fallback methods
    def _load_journals_from_json(self) -> List[JournalEntry]:
        """Load journals from JSON file (fallback)"""
        if os.path.exists(self.json_files['journals']):
            try:
                with open(self.json_files['journals'], 'r') as f:
                    data = json.load(f)
                    return [JournalEntry(**entry) for entry in data]
            except Exception:
                return []
        return []
    
    def _save_journals_to_json(self, journals: List[JournalEntry]):
        """Save journals to JSON file (fallback)"""
        with open(self.json_files['journals'], 'w') as f:
            json.dump([journal.dict() for journal in journals], f, indent=2)
    
    def _create_journal_json(self, journal_data: Dict[str, Any]) -> Optional[JournalEntry]:
        """Create journal using JSON storage (fallback)"""
        journals = self._load_journals_from_json()
        
        journal_id = f"j_{int(datetime.now().timestamp())}_{hash(str(datetime.now())) % 1000000:06d}"
        now = datetime.now().isoformat()
        
        new_journal = JournalEntry(
            id=journal_id,
            title=journal_data.get('title', ''),
            content=journal_data.get('content', ''),
            created_at=now,
            updated_at=now,
            word_count=len(journal_data.get('content', '').split()),
            keywords=journal_data.get('keywords', {}),
            user_id=journal_data.get('user_id')
        )
        
        journals.append(new_journal)
        self._save_journals_to_json(journals)
        return new_journal
    
    def _update_journal_json(self, journal_id: str, journal_data: Dict[str, Any]) -> Optional[JournalEntry]:
        """Update journal using JSON storage (fallback)"""
        journals = self._load_journals_from_json()
        journal = next((j for j in journals if j.id == journal_id), None)
        
        if not journal:
            return None
        
        # Update fields
        if 'title' in journal_data:
            journal.title = journal_data['title']
        if 'content' in journal_data:
            journal.content = journal_data['content']
        
        journal.updated_at = datetime.now().isoformat()
        journal.word_count = len(journal.content.split())
        journal.keywords = journal_data.get('keywords', journal.keywords)
        
        self._save_journals_to_json(journals)
        return journal
    
    def _delete_journal_json(self, journal_id: str) -> bool:
        """Delete journal using JSON storage (fallback)"""
        journals = self._load_journals_from_json()
        journals = [j for j in journals if j.id != journal_id]
        self._save_journals_to_json(journals)
        return True
    
    def _search_journals_json(self, query: str) -> List[JournalEntry]:
        """Search journals using JSON storage (fallback)"""
        journals = self._load_journals_from_json()
        query_lower = query.lower()
        
        matching_journals = []
        for journal in journals:
            if (query_lower in journal.title.lower() or 
                query_lower in journal.content.lower() or
                any(query_lower in keyword.lower() for keyword in journal.keywords.keys())):
                matching_journals.append(journal)
        
        return matching_journals
    
    # Feed operations (similar pattern)
    def get_all_feed_subscriptions(self, user_id: Optional[str] = None) -> List[FeedSubscription]:
        def db_operation():
            return self.db_service.get_all_feed_subscriptions(user_id)
        
        def json_operation():
            return self._load_feeds_from_json()
        
        return self._try_database_operation(db_operation, json_operation)
    
    def create_feed_subscription(self, feed_data: Dict[str, Any]) -> Optional[FeedSubscription]:
        def db_operation():
            return self.db_service.create_feed_subscription(feed_data)
        
        def json_operation():
            return self._create_feed_json(feed_data)
        
        return self._try_database_operation(db_operation, json_operation)
    
    def delete_feed_subscription(self, subscription_id: str) -> bool:
        def db_operation():
            return self.db_service.delete_feed_subscription(subscription_id)
        
        def json_operation():
            return self._delete_feed_json(subscription_id)
        
        return self._try_database_operation(db_operation, json_operation)
    
    # JSON fallback methods for feeds
    def _load_feeds_from_json(self) -> List[FeedSubscription]:
        if os.path.exists(self.json_files['feeds']):
            try:
                with open(self.json_files['feeds'], 'r') as f:
                    data = json.load(f)
                    return [FeedSubscription(**feed) for feed in data]
            except Exception:
                return []
        return []
    
    def _save_feeds_to_json(self, feeds: List[FeedSubscription]):
        with open(self.json_files['feeds'], 'w') as f:
            json.dump([feed.dict() for feed in feeds], f, indent=2)
    
    def _create_feed_json(self, feed_data: Dict[str, Any]) -> Optional[FeedSubscription]:
        feeds = self._load_feeds_from_json()
        
        feed_id = f"feed_{int(datetime.now().timestamp())}_{hash(str(datetime.now())) % 1000000:06d}"
        now = datetime.now().isoformat()
        
        new_feed = FeedSubscription(
            id=feed_id,
            url=feed_data.get('url', ''),
            title=feed_data.get('title', ''),
            description=feed_data.get('description', ''),
            last_updated=now,
            is_active=feed_data.get('is_active', True),
            user_id=feed_data.get('user_id')
        )
        
        feeds.append(new_feed)
        self._save_feeds_to_json(feeds)
        return new_feed
    
    def _delete_feed_json(self, subscription_id: str) -> bool:
        feeds = self._load_feeds_from_json()
        feeds = [f for f in feeds if f.id != subscription_id]
        self._save_feeds_to_json(feeds)
        return True
    
    # Article operations
    def get_all_articles(self, user_id: Optional[str] = None) -> List[Article]:
        def db_operation():
            return self.db_service.get_all_articles(user_id)
        
        def json_operation():
            return self._load_articles_from_json()
        
        return self._try_database_operation(db_operation, json_operation)
    
    def create_article(self, article_data: Dict[str, Any]) -> Optional[Article]:
        def db_operation():
            return self.db_service.create_article(article_data)
        
        def json_operation():
            return self._create_article_json(article_data)
        
        return self._try_database_operation(db_operation, json_operation)
    
    # JSON fallback methods for articles
    def _load_articles_from_json(self) -> List[Article]:
        if os.path.exists(self.json_files['articles']):
            try:
                with open(self.json_files['articles'], 'r') as f:
                    data = json.load(f)
                    return [Article(**article) for article in data]
            except Exception:
                return []
        return []
    
    def _create_article_json(self, article_data: Dict[str, Any]) -> Optional[Article]:
        articles = self._load_articles_from_json()
        
        article_id = f"article_{int(datetime.now().timestamp())}_{hash(str(datetime.now())) % 1000000:06d}"
        
        new_article = Article(
            id=article_id,
            title=article_data.get('title', ''),
            source=article_data.get('source', ''),
            snippet=article_data.get('snippet', ''),
            date=article_data.get('date', datetime.now().isoformat().split('T')[0]),
            type=article_data.get('type', 'rss'),
            url=article_data.get('url'),
            feed_id=article_data.get('feed_id'),
            content=article_data.get('content'),
            author=article_data.get('author'),
            tags=article_data.get('tags', []),
            user_id=article_data.get('user_id')
        )
        
        articles.append(new_article)
        self._save_articles_to_json(articles)
        return new_article
    
    def _save_articles_to_json(self, articles: List[Article]):
        with open(self.json_files['articles'], 'w') as f:
            json.dump([article.dict() for article in articles], f, indent=2)
    
    # Document operations
    def get_all_documents(self, user_id: Optional[str] = None) -> List[Document]:
        def db_operation():
            return self.db_service.get_all_documents(user_id)
        
        def json_operation():
            return self._load_documents_from_json()
        
        return self._try_database_operation(db_operation, json_operation)
    
    def create_document(self, document_data: Dict[str, Any]) -> Optional[Document]:
        def db_operation():
            return self.db_service.create_document(document_data)
        
        def json_operation():
            return self._create_document_json(document_data)
        
        return self._try_database_operation(db_operation, json_operation)
    
    def delete_document(self, document_id: str) -> bool:
        def db_operation():
            return self.db_service.delete_document(document_id)
        
        def json_operation():
            return self._delete_document_json(document_id)
        
        return self._try_database_operation(db_operation, json_operation)
    
    # JSON fallback methods for documents
    def _load_documents_from_json(self) -> List[Document]:
        if os.path.exists(self.json_files['documents']):
            try:
                with open(self.json_files['documents'], 'r') as f:
                    data = json.load(f)
                    return [Document(**doc) for doc in data]
            except Exception:
                return []
        return []
    
    def _create_document_json(self, document_data: Dict[str, Any]) -> Optional[Document]:
        documents = self._load_documents_from_json()
        
        doc_id = f"doc_{int(datetime.now().timestamp())}_{hash(str(datetime.now())) % 1000000:06d}"
        now = datetime.now().isoformat()
        
        new_document = Document(
            id=doc_id,
            name=document_data.get('name', ''),
            type=document_data.get('type', ''),
            size=document_data.get('size', 0),
            upload_date=now,
            content=document_data.get('content'),
            status=document_data.get('status', 'ready'),
            user_id=document_data.get('user_id')
        )
        
        documents.append(new_document)
        self._save_documents_to_json(documents)
        return new_document
    
    def _delete_document_json(self, document_id: str) -> bool:
        documents = self._load_documents_from_json()
        documents = [d for d in documents if d.id != document_id]
        self._save_documents_to_json(documents)
        return True
    
    def _save_documents_to_json(self, documents: List[Document]):
        with open(self.json_files['documents'], 'w') as f:
            json.dump([doc.dict() for doc in documents], f, indent=2)

# Global hybrid service instance
hybrid_service = HybridService()




