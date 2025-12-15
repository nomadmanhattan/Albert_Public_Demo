import logging
import os.path
import sqlite3
import pickle
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class EmbeddingCache:
    def __init__(self, db_path: str = "data/embeddings.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Table for Email Embeddings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    email_id TEXT PRIMARY KEY,
                    vector BLOB,
                    created_at REAL
                )
            """)
            # Table for Query Embeddings (Query Memory)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    query_text TEXT PRIMARY KEY,
                    vector BLOB,
                    created_at REAL
                )
            """)
            conn.commit()

    def get_emails(self, email_ids: List[str]) -> Dict[str, bytes]:
        if not email_ids:
            return {}
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ",".join(["?"] * len(email_ids))
            cursor = conn.execute(f"SELECT email_id, vector FROM embeddings WHERE email_id IN ({placeholders})", email_ids)
            return {row[0]: row[1] for row in cursor.fetchall()}

    def set_emails(self, embeddings: Dict[str, bytes]):
        if not embeddings:
            return
        data = [(eid, vec, time.time()) for eid, vec in embeddings.items()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("INSERT OR REPLACE INTO embeddings (email_id, vector, created_at) VALUES (?, ?, ?)", data)
            conn.commit()

    def get_query(self, query_text: str) -> Optional[bytes]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT vector FROM queries WHERE query_text = ?", (query_text,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_query(self, query_text: str, vector: bytes):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO queries (query_text, vector, created_at) VALUES (?, ?, ?)", 
                         (query_text, vector, time.time()))
            conn.commit()

class EmailAggregator:
    def __init__(self):
        self.creds = None
        self.service = None
        self.cache = EmbeddingCache()
        self._authenticate()
        
        # Simple in-memory cache for fetch_emails to handle short-term repeated calls
        # Key: (tuple(sorted(labels)), days), Value: (timestamp, data)
        self._fetch_memory_cache = {} 
        self._memory_ttl = 300 # 5 minutes

    def _authenticate(self):
        """Authenticates with Gmail API using token.json."""
        # Look for token.json in likely locations
        possible_paths = [
            'token.json',
            'backend/token.json',
            os.path.join(os.path.dirname(__file__), '../../token.json')
        ]
        
        token_path = None
        for path in possible_paths:
            if os.path.exists(path):
                token_path = path
                break
        
        if token_path:
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # Auto-refresh if expired
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    logger.info("Token expired. Refreshing...")
                    self.creds.refresh(Request())
                    # Save refreshed token back to file
                    with open(token_path, 'w') as token:
                        token.write(self.creds.to_json())
                    logger.info("Token refreshed and saved.")
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
        else:
            logger.warning(f"token.json not found in {possible_paths}")
        
        if self.creds and self.creds.valid:
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail API service initialized.")
        else:
            logger.warning("Gmail credentials not valid or token.json missing. Email fetching will fail.")

    def fetch_emails(self, days: int = 1, max_results: int = 50) -> list[dict]:
        """
        Fetches a broad list of emails from the last X days to be used as candidates for semantic search.
        """
        # Check in-memory cache
        # Cache key simplified since labels are gone
        cache_key = (days, max_results)
        if cache_key in self._fetch_memory_cache:
            ts, data = self._fetch_memory_cache[cache_key]
            if time.time() - ts < self._memory_ttl:
                logger.info("Using in-memory cache for fetch_emails.")
                return data

        if not self.service:
            logger.error("Gmail service not initialized. Cannot fetch emails.")
            return []

        logger.info(f"Fetching emails (Last {days} days, Max {max_results})")
        
        # Calculate date query (Gmail search format: "after:YYYY/MM/DD")
        cutoff_date = datetime.now() - timedelta(days=days)
        date_query = f"after:{cutoff_date.strftime('%Y/%m/%d')}"
        query = date_query
        
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            email_data = []
            for msg in messages:
                # Get full message details
                # batching could be better here but simple get is safer for now
                try:
                    txt = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                    
                    payload = txt['payload']
                    headers = payload.get('headers', [])
                    
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
                    date_str = next((h['value'] for h in headers if h['name'] == 'Date'), "")
                    snippet = txt.get('snippet', '')
                    
                    email_data.append({
                        "id": msg['id'],
                        "subject": subject,
                        "sender": sender,
                        "date": date_str,
                        "body": snippet, 
                        # "labels": labels # Removed
                    })
                except Exception as e:
                    logger.warning(f"Failed to fetch details for msg {msg['id']}: {e}")
                
            logger.info(f"Fetched {len(email_data)} emails.")
            
            # Update memory cache
            self._fetch_memory_cache[cache_key] = (time.time(), email_data)
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def semantic_search(self, query: str, days: int = 14, max_results: int = 50) -> list[dict]:
        """
        Performs semantic search on recent emails using Gemini embeddings with SQLite Caching.
        """
        import google.generativeai as genai
        import numpy as np
        
        # Ensure API key is set
        if not os.getenv("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY not found. Cannot perform semantic search.")
            return []
            
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # 1. Fetch a broad set of recent emails
        candidates = self.fetch_emails(days=days, max_results=50) # Assuming we want to search all recent emails
        
        if not candidates:
            return []
            
        logger.info(f"Ranking {len(candidates)} emails for query: '{query}'")
        
        try:
            # 2. Get Query Embedding (Check Cache First)
            query_embedding_bytes = self.cache.get_query(query)
            
            if query_embedding_bytes:
                logger.info("Using cached query embedding.")
                query_embedding = np.frombuffer(query_embedding_bytes, dtype=np.float32)
            else:
                logger.info("Generating new query embedding via Gemini...")
                # Note: 'retrieval_query' task type is important
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=query,
                    task_type="retrieval_query"
                )
                query_embedding = np.array(result['embedding'], dtype=np.float32)
                self.cache.set_query(query, query_embedding.tobytes())
            
            # 3. Get Candidate Embeddings (Check Cache First)
            candidate_ids = [e['id'] for e in candidates]
            cached_vectors = self.cache.get_emails(candidate_ids)
            
            missing_indices = []
            missing_texts = []
            final_embeddings = [None] * len(candidates)
            
            # Fill in cached ones
            for i, email in enumerate(candidates):
                if email['id'] in cached_vectors:
                    final_embeddings[i] = np.frombuffer(cached_vectors[email['id']], dtype=np.float32)
                else:
                    missing_indices.append(i)
                    missing_texts.append(f"Subject: {email['subject']}\nSnippet: {email['body']}")
            
            if missing_indices:
                logger.info(f"Generating embeddings for {len(missing_indices)} missing emails...")
                # Batch embed
                batch_result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=missing_texts,
                    task_type="retrieval_document"
                )
                
                new_embeddings = batch_result['embedding']
                
                # Store and update list
                updates = {}
                for idx, embedding_list in enumerate(new_embeddings):
                    original_idx = missing_indices[idx]
                    vec = np.array(embedding_list, dtype=np.float32)
                    final_embeddings[original_idx] = vec
                    updates[candidates[original_idx]['id']] = vec.tobytes()
                
                self.cache.set_emails(updates)
            else:
                logger.info(f"Using cached embeddings for all {len(candidates)} emails.")
            
            # 4. Calculate Cosine Similarity
            def cosine_similarity(v1, v2):
                return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                
            scored_emails = []
            for i, email in enumerate(candidates):
                if final_embeddings[i] is None:
                    continue # Should not happen
                score = cosine_similarity(query_embedding, final_embeddings[i])
                scored_emails.append((score, email))
            
            # 5. Sort and Filter
            scored_emails.sort(key=lambda x: x[0], reverse=True)
            
            # Return top N
            top_emails = [email for score, email in scored_emails[:max_results]]
            logger.info(f"Found {len(top_emails)} relevant emails.")
            return top_emails
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            import traceback
            traceback.print_exc()
            return []
