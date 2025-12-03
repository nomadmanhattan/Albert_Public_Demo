import logging
from app.agents.email_aggregator import EmailAggregator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_labels():
    logger.info("Listing Gmail labels...")
    aggregator = EmailAggregator()
    
    if not aggregator.service:
        logger.error("Gmail service not initialized.")
        return

    try:
        results = aggregator.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            logger.info('No labels found.')
        else:
            logger.info('Labels:')
            for label in labels:
                logger.info(f" - {label['name']}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    list_labels()
