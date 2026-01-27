# JamieBot/app/api/routes.py
from fastapi import APIRouter, HTTPException
from app.schemas import AIRequest, AIResponse
from app.orchestrator import Orchestrator
from app.state_machine.states import ConversationState
from app.services.redis_service import RedisService

router = APIRouter()
orchestrator = Orchestrator()
redis_service = RedisService()

@router.post("/process-message", response_model=AIResponse)
def process_message(request: AIRequest):
    try:
        # 1. Retrieve History from Redis
        history = redis_service.get_history(request.user_id)
        
        # 2. Validate State
        if request.current_state not in ConversationState.__members__:
            raise HTTPException(status_code=400, detail=f"Invalid state: {request.current_state}")
        
        current_state = ConversationState[request.current_state]
        
        # 3. Process Message (Pass History)
        result = orchestrator.process_message(
            user_message=request.message,
            current_state=current_state,
            extracted_attributes=request.user_attributes,
            history=history # <--- Context Injection
        )
        
        # 4. Save Interaction to Redis (Memory)
        # Save User Message
        redis_service.add_message(request.user_id, "user", request.message)
        # Save Bot Reply
        redis_service.add_message(request.user_id, "assistant", result["reply"])
        
        return AIResponse(
            reply=result["reply"],
            next_state=result["next_state"],
            extracted_attributes=result.get("extracted_attributes"),
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear-history/{user_id}")
def clear_history(user_id: str):
    """Utility to reset a user's memory"""
    redis_service.clear_history(user_id)
    return {"status": "cleared"}