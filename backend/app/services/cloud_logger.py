import logging
import os
import json
from datetime import datetime
from google.cloud import logging as cloud_logging
from google.oauth2 import service_account

# Configure local logger for fallback
logger = logging.getLogger(__name__)

class CloudLogger:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "albert-the-butler-mvp")
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "certs/albert-logger-GCP-key.json")
        self.client = None
        self.logger = None
        self.log_name = "albert_session_logs"

        try:
            if os.path.exists(self.creds_path):
                creds = service_account.Credentials.from_service_account_file(self.creds_path)
                self.client = cloud_logging.Client(project=self.project_id, credentials=creds)
                self.logger = self.client.logger(self.log_name)
                logger.info(f"Connected to Google Cloud Logging: {self.log_name}")
            else:
                logger.warning(f"GCP Credentials not found at {self.creds_path}. Cloud logging disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize CloudLogger: {e}")

    def log_struct(self, data: dict):
        """
        Writes a structured log entry to Cloud Logging.
        """
        if not self.logger:
            return

        try:
            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()
            
            # Write structured log
            self.logger.log_struct(data)
            logger.info(f"Logged structured data to Cloud Logging.")
        except Exception as e:
            logger.error(f"Failed to write to Cloud Logging: {e}")
