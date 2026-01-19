# JamieBot/app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# INPUT SCHEMA (Request)
class AIRequest(BaseModel):
    """
    Input payload sent from the backend to the AI Setter service.
    This represents one turn in the conversation.
    """
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="Latest message sent by the user")
    current_state: str = Field(..., description="Current conversation state (e.g., RAPPORT, QUAL_LOCATION)")
    user_attributes: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Collected user attributes"
    )

# OUTPUT SCHEMA (Response)
class AIResponse(BaseModel):
    """
    Output payload returned by the AI Setter service to the backend.
    """
    reply: str = Field(..., description="The message the AI should send to the user")
    next_state: str = Field(..., description="Next conversation state decided by the state machine")
    extracted_attributes: Optional[Dict[str, Any]] = Field( # <--- Change str to Any
        default=None,
        description="New user attributes"
    )
