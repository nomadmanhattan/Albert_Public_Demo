import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.agents.concierge_agent import ConciergeAgent

async def run_e2e_test():
    logger.info("Starting End-to-End Test...")
    
    agent = ConciergeAgent()
    
    # User query that triggers the full flow
    user_query = "Create a digest for my emails updates from the last 1 day. Then create a podcast."
    
    logger.info(f"User Query: {user_query}")
    
    try:
    
        # Use gemini-2.5-flash 
        result = await agent.process_request(user_query)
        
        logger.info("E2E Test Completed!")
        logger.info(f"Agent Response: {result['response']}")
        
    except Exception as e:
        logger.error(f"E2E Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
