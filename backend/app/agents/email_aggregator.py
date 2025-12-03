import logging
import os.path
import base64
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class EmailAggregator:
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

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

    def fetch_emails(self, labels: list[str], days: int = 1, max_results: int = 50) -> list[dict]:
        """
        Fetches emails matching the given labels from the last X days.
        """
        if not self.service:
            logger.error("Gmail service not initialized. Cannot fetch emails.")
            return []

        logger.info(f"Fetching emails for labels: {labels} (Last {days} days, Max {max_results})")
        
        # Calculate date query (Gmail search format: "after:YYYY/MM/DD")
        cutoff_date = datetime.now() - timedelta(days=days)
        date_query = f"after:{cutoff_date.strftime('%Y/%m/%d')}"
        
        # Resolve label names to IDs
        label_ids = []
        try:
            results = self.service.users().labels().list(userId='me').execute()
            gmail_labels = results.get('labels', [])
            
            for requested_label in labels:
                # Exact match
                for gl in gmail_labels:
                    if gl['name'] == requested_label:
                        label_ids.append(gl['id'])
                    # Prefix match for sub-labels
                    elif gl['name'].startswith(f"{requested_label}/"):
                        label_ids.append(gl['id'])
            
            # Remove duplicates
            label_ids = list(set(label_ids))
            logger.info(f"Resolved label IDs: {label_ids}")
            
        except Exception as e:
            logger.error(f"Failed to resolve label IDs: {e}")

        # Calculate date query (Gmail search format: "after:YYYY/MM/DD")
        cutoff_date = datetime.now() - timedelta(days=days)
        date_query = f"after:{cutoff_date.strftime('%Y/%m/%d')}"
        
        # Logics for handle labels:
        # Can't mix `labelIds` (list) and `q` (string) easily in the same call if intent is to useOR logic for labels AND date logic.
        # `labelIds` in list() is AND logic.
        # Thus stick to `q` but use `label:ID` which is safer than `label:NAME`.
        
        if label_ids:
            label_query = " OR ".join([f'label:{lid}' for lid in label_ids])
            query = f"({label_query}) {date_query}"
        else:
            # Fallback to name if ID resolution failed (though unlikely if service works)
            logger.warning("No label IDs resolved. Falling back to name search.")
            label_query = " OR ".join([f'label:"{l}"' for l in labels])
            query = f"({label_query}) {date_query}"
        
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            email_data = []
            for msg in messages:
                # Get full message details
                txt = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                payload = txt['payload']
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), "")
                
                # Extract body (snippet for now, or full text if needed)
                snippet = txt.get('snippet', '')
                
                email_data.append({
                    "id": msg['id'],
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "body": snippet, # Using snippet for efficiency
                    "labels": labels # Simplified, actual labels are in txt['labelIds']
                })
                
            logger.info(f"Fetched {len(email_data)} emails.")
            return email_data
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def semantic_search(self, query: str, days: int = 14, max_results: int = 50) -> list[dict]:
        """
        Performs semantic search on recent emails using Gemini embeddings.
        """
        import google.generativeai as genai
        import numpy as np
        
        # Ensure API key is set
        if not os.getenv("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY not found. Cannot perform semantic search.")
            return []
            
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # 1. Fetch a broad set of recent emails (e.g., last 14 days, max 50)
        # Use a broad search to get candidates. Shall revisit this logic after initiatl user adoption and usages are observed.
        candidates = self.fetch_emails(labels=[], days=days, max_results=50)
        
        if not candidates:
            return []
            
        logger.info(f"Ranking {len(candidates)} emails for query: '{query}'")
        
        try:
            # 2. Embed the query
            query_embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query"
            )['embedding']
            
            # 3. Embed the candidates (Subject + Snippet)
            # Batching could be added here if needed, for the time being, as long as <50, keep it as it is. 
            candidate_texts = [f"Subject: {e['subject']}\nSnippet: {e['body']}" for e in candidates]
            
            candidate_embeddings = genai.embed_content(
                model="models/text-embedding-004",
                content=candidate_texts,
                task_type="retrieval_document"
            )['embedding']
            
            # 4. Calculate Cosine Similarity
            def cosine_similarity(v1, v2):
                return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                
            scored_emails = []
            for i, email in enumerate(candidates):
                score = cosine_similarity(query_embedding, candidate_embeddings[i])
                scored_emails.append((score, email))
            
            # 5. Sort and Filter
            scored_emails.sort(key=lambda x: x[0], reverse=True)
            
            # Return top N
            top_emails = [email for score, email in scored_emails[:max_results]]
            logger.info(f"Found {len(top_emails)} relevant emails.")
            return top_emails
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
