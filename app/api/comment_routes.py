# JamieBot/app/api/comment_routes.py
from fastapi import APIRouter, HTTPException
from app.schemas import CommentRequest, CommentResponse
from app.comment_system.logic import CommentLogic

router = APIRouter()
logic = CommentLogic()

@router.post("/process-comment", response_model=CommentResponse)
def process_comment(request: CommentRequest):
    try:
        # 1. Detect Intent
        intent = logic.detect_intent(request.comment_text)
        
        # 2. Select Template
        reply = logic.select_template(intent, request.platform)
        
        return CommentResponse(
            reply_text=reply,
            intent_detected=intent,
            action="POST_REPLY"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))