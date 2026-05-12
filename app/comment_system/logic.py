# JamieBot/app/comment_system/logic.py
import random
from app.comment_system.data import KEYWORDS, TEMPLATES

class CommentLogic:
    def normalize(self, text: str) -> str:
        return text.lower().strip()

    def detect_intent(self, text: str) -> str:
        text = self.normalize(text)
        
        # Priority Order: Price > Eligibility > Interest > Generic
        if any(k in text for k in KEYWORDS["PRICE"]):
            return "PRICE"
            
        if any(k in text for k in KEYWORDS["ELIGIBILITY"]):
            return "ELIGIBILITY"
            
        if any(k in text for k in KEYWORDS["INTEREST"]):
            return "INTEREST"
            
        if any(k in text for k in KEYWORDS["GENERIC"]):
            return "GENERIC"
            
        return "UNKNOWN"

    def select_template(self, intent: str, platform: str) -> str:
        # Normalize platform to uppercase to handle "instagram", "Instagram", "INSTAGRAM"
        platform_key = platform.upper().strip()

        # 1. Handle YouTube Override
        if platform_key == "YOUTUBE":
            return TEMPLATES["YOUTUBE_OVERRIDE"]
        
        # 2. Fallback if intent missing
        if intent not in TEMPLATES:
            intent = "UNKNOWN"
            
        # 3. Pick random template
        options = TEMPLATES[intent]
        base_reply = random.choice(options)
        
        # 4. Facebook Adaptation (Optional check using string)
        if platform_key == "FACEBOOK":
            # Example adaptation if needed later
            pass
            
        return base_reply