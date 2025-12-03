import logging
from app.agents.email_aggregator import EmailAggregator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gmail_fetch():
    logger.info("Testing EmailAggregator...")
    aggregator = EmailAggregator()
    
    # Test fetching from 'To Read List/TL;DR - Verge'
    # Fetching last 1 day
    emails = aggregator.fetch_emails(labels=["To Read List/TL;DR - Verge"], days=1)
    
    if emails:
        logger.info(f"Successfully fetched {len(emails)} emails.")
        for email in emails[:3]: # Print first 3
            logger.info(f" - {email['subject']} ({email['sender']})")
    else:
        logger.info("No emails found (or fetch failed). Check logs.")

if __name__ == "__main__":
    test_gmail_fetch()
