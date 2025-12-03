import json
import os
import logging

logger = logging.getLogger(__name__)

class UserContextService:
    def __init__(self, context_file: str = "data/user_context.json"):
        self.context_file = context_file
        os.makedirs(os.path.dirname(self.context_file), exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.context_file):
            with open(self.context_file, 'w') as f:
                json.dump({}, f)

    def get_context(self) -> dict:
        try:
            with open(self.context_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load context: {e}")
            return {}

    def update_context(self, updates: dict):
        current = self.get_context()
        current.update(updates)
        try:
            with open(self.context_file, 'w') as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    def get_last_labels(self) -> list[str]:
        return self.get_context().get("last_used_labels", [])

    def set_last_labels(self, labels: list[str]):
        self.update_context({"last_used_labels": list(labels)})
