import logging
import os
from dotenv import load_dotenv
from app.agents.email_aggregator import EmailAggregator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_semantic_search():
    load_dotenv()
    logger.info("🚀 Starting Semantic Search Debug...")
    
    # Check API Key
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("❌ GOOGLE_API_KEY not found in environment.")
        return

    aggregator = EmailAggregator()
    
    if not aggregator.service:
        logger.error("❌ Gmail service not initialized.")
        return

    query = "AI news"
    days = 14
    
    logger.info(f"🔎 Searching for: '{query}' (Last {days} days)")
    
    try:
        results = aggregator.semantic_search(query, days=days, max_results=5)
        
        if results:
            logger.info(f"✅ Found {len(results)} relevant emails:")
            for i, email in enumerate(results):
                logger.info(f"   {i+1}. [{email['date']}] {email['subject']} (from {email['sender']})")
        else:
            logger.warning("⚠️ No relevant emails found.")
            
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_semantic_search()
