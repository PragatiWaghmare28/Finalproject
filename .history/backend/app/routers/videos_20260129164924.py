from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid

from ..database import get_db
from ..models import Video, VideoStatus, VideoSource
from ..schemas import VideoProcessUrl, VideoResponse, VideoStatusResponse, VideoUploadResponse
from ..config import get_settings
from ..dependencies import require_api_key, rate_limit_process
from ..services.video_processor import process_video_task

router = APIRouter(prefix="/videos", tags=["Videos"])
settings = get_settings()


@router.get("", response_model=List[VideoResponse])
def get_all_videos(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all videos, optionally filtered by status"""
    query = db.query(Video).order_by(Video.created_at.desc())
    
    if status:
        query = query.filter(Video.status == status)
    
    videos = query.all()
    return [VideoResponse(**v.to_dict()) for v in videos]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: str, db: Session = Depends(get_db)):
    """Get a single video by ID"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoResponse(**video.to_dict())


@router.post("/process-url", response_model=VideoUploadResponse)
def process_video_url(
    data: VideoProcessUrl,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _auth=Depends(require_api_key),
    _rl=Depends(rate_limit_process)
):
    """Process a video from URL (YouTube, Vimeo, etc.)"""
    # Create video record
    video = Video(
        id=str(uuid.uuid4()),
        title=data.title or "Processing...",
        source_type=VideoSource.YOUTUBE,
        source_url=data.url,
        status=VideoStatus.PENDING,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # Start background processing
    background_tasks.add_task(process_video_task, video.id, data.url)
    
    return VideoUploadResponse(
        id=video.id,
        title=video.title,
        status=video.status,
        message="Video processing started"
    )


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None),
    db: Session = Depends(get_db),
    _auth=Depends(require_api_key),
    _rl=Depends(rate_limit_process)
):
    """Upload a video file (MP4, etc.)"""
    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "video/quicktime"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.upload_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Create video record
    video = Video(
        id=str(uuid.uuid4()),
        title=title or file.filename,
        source_type=VideoSource.UPLOAD,
        file_path=file_path,
        status=VideoStatus.PENDING,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # Start background processing
    background_tasks.add_task(process_video_task, video.id, file_path, is_local=True)
    
    return VideoUploadResponse(
        id=video.id,
        title=video.title,
        status=video.status,
        message="Video upload successful, processing started"
    )


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(video_id: str, db: Session = Depends(get_db)):
    """Get video processing status"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoStatusResponse(
        id=video.id,
        status=video.status,
        message=video.error_message if video.status == "failed" else None
    )


@router.get("/{video_id}/transcript")
def get_video_transcript(video_id: str, db: Session = Depends(get_db)):
    """Get video transcript"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != VideoStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Video processing not completed")
    
    return {"video_id": video.id, "transcript": video.transcript}


@router.post("/{video_id}/like")
def toggle_like(video_id: str, db: Session = Depends(get_db), _auth=Depends(require_api_key)):
    """Toggle like status of a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video.is_liked = not video.is_liked
    db.commit()
    
    return {"video_id": video.id, "is_liked": video.is_liked}
@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db), _auth=Depends(require_api_key)):
    """Delete a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete file if exists
    if video.file_path and os.path.exists(video.file_path):
        os.remove(video.file_path)
    
    db.delete(video)
    db.commit()
    
    return {"message": "Video deleted successfully"}
