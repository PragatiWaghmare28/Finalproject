from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import ChatMessage, Video, VideoStatus
from ..schemas import ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse
from ..services.rag_service import get_rag_response
from ..dependencies import require_api_key, rate_limit_chat

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatMessageResponse)
async def send_message(
    data: ChatMessageRequest,
    db: Session = Depends(get_db),
    _auth=Depends(require_api_key),
    _rl=Depends(rate_limit_chat)
):
    """Send a message and get AI response about a video"""
    # Verify video exists and is processed
    video = db.query(Video).filter(Video.id == data.videoId).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != VideoStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Video processing not completed")
    
    # Save user message
    user_msg = ChatMessage(
        video_id=data.videoId,
        role="user",
        content=data.message
    )
    db.add(user_msg)
    
    # Get AI response using RAG
    response = await get_rag_response(data.videoId, data.message, db)
    
    # Save assistant message
    assistant_msg = ChatMessage(
        video_id=data.videoId,
        role="assistant",
        content=response["message"],
        references=response.get("references")
    )
    db.add(assistant_msg)
    db.commit()
    
    return ChatMessageResponse(
        message=response["message"],
        references=response.get("references")
    )


@router.get("/{video_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(video_id: str, db: Session = Depends(get_db), _auth=Depends(require_api_key)):
    """Get chat history for a video"""
    messages = db.query(ChatMessage).filter(
        ChatMessage.video_id == video_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return ChatHistoryResponse(
        video_id=video_id,
        messages=[m.to_dict() for m in messages]
    )


@router.delete("/{video_id}/history")
def clear_chat_history(video_id: str, db: Session = Depends(get_db), _auth=Depends(require_api_key)):
    """Clear chat history for a video"""
    db.query(ChatMessage).filter(ChatMessage.video_id == video_id).delete()
    db.commit()
    
    return {"message": "Chat history cleared"}
