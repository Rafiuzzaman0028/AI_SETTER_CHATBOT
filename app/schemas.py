# JamieBot/app/schemas.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class Message(BaseModel):
    role: str
    content: str

# INPUT SCHEMA
class AIRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="Latest message sent by the user")
    current_state: str = Field(..., description="Current conversation state")
    user_attributes: Optional[Dict[str, Any]] = Field(default=None, description="Collected user attributes")
    history: Optional[List[Message]] = Field(default=[])

# OUTPUT SCHEMA
class AIResponse(BaseModel):
    reply: str
    next_state: str
    extracted_attributes: Optional[Dict[str, Any]] = Field(default=None, description="New user attributes")
    progress_score: int = Field(..., description="Lead progress from 0 to 100")

class Platform(str, Enum):
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    YOUTUBE = "YOUTUBE"

class CommentRequest(BaseModel):
    platform: Optional[str] = "UNKNOWN"
    user_id: str
    comment_text: str
    post_id: Optional[str] = None

class CommentResponse(BaseModel):
    reply_text: str
    intent_detected: str
    action: str = "POST_REPLY" # or "IGNORE"