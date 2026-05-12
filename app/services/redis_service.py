# JamieBot/app/services/redis_service.py
import redis
import json
from typing import List, Dict
from app.config import Config

class RedisService:
    def __init__(self):
        self.client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True # Returns strings instead of bytes
        )
        self.ttl = Config.SESSION_TTL

    def get_history(self, user_id: str) -> List[Dict[str, str]]:
        """
        Retrieves full chat history for a user.
        """
        key = f"jamie_chat:{user_id}"
        # Get all items in the list (0 to -1)
        raw_history = self.client.lrange(key, 0, -1)
        return [json.loads(msg) for msg in raw_history]

    def add_message(self, user_id: str, role: str, content: str):
        """
        Appends a message to the history.
        """
        key = f"jamie_chat:{user_id}"
        message = {"role": role, "content": content}
        
        # Push to right end of list
        self.client.rpush(key, json.dumps(message))
        
        # Reset Expiry (keep session alive)
        self.client.expire(key, self.ttl)

    def clear_history(self, user_id: str):
        """
        Clears history (useful when resetting flow).
        """
        key = f"jamie_chat:{user_id}"
        self.client.delete(key)