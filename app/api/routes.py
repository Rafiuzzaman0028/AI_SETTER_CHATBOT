# JamieBot/app/api/routes.py
from fastapi import APIRouter, HTTPException
from app.schemas import AIRequest, AIResponse
from app.orchestrator import Orchestrator
from app.state_machine.states import ConversationState

router = APIRouter()

# Initialize orchestrator once
orchestrator = Orchestrator()

@router.post("/process-message", response_model=AIResponse)
def process_message(request: AIRequest):
    try:
        # Convert state string to enum
        if request.current_state not in ConversationState.__members__:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid conversation state: {request.current_state}",
            )
            
        current_state = ConversationState[request.current_state]
        
        result = orchestrator.process_message(
            user_message=request.message,
            current_state=current_state,
            extracted_attributes=request.user_attributes,
        )
        
        return AIResponse(
            reply=result["reply"],
            next_state=result["next_state"],
            extracted_attributes=result.get("extracted_attributes"),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )