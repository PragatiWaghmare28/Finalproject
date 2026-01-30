from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Quiz, QuizAttempt, Video, VideoStatus
from ..schemas import QuizGenerateRequest, QuizResponse, QuizSubmitRequest, QuizResultResponse
from ..services.quiz_service import generate_quiz_questions, analyze_quiz_results
from ..dependencies import require_api_key, rate_limit_quiz

router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    data: QuizGenerateRequest,
    db: Session = Depends(get_db),
    _auth=Depends(require_api_key),
    _rl=Depends(rate_limit_quiz)
):
    """Generate a quiz for a video using AI"""
    # Verify video exists and is processed
    video = db.query(Video).filter(Video.id == data.videoId).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != VideoStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Video processing not completed")
    
    # Generate questions using AI
    questions = await generate_quiz_questions(
        video_id=data.videoId,
        transcript=video.transcript,
        count=data.questionCount
    )
    
    # Save quiz
    quiz = Quiz(
        video_id=data.videoId,
        questions=questions
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    return QuizResponse(**quiz.to_dict(include_answers=False))


@router.get("/{quiz_id}", response_model=QuizResponse)
def get_quiz(quiz_id: str, db: Session = Depends(get_db)):
    """Get quiz questions (without correct answers)"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return QuizResponse(**quiz.to_dict(include_answers=False))


@router.post("/{quiz_id}/submit", response_model=QuizResultResponse)
async def submit_quiz(
    quiz_id: str,
    data: QuizSubmitRequest,
    db: Session = Depends(get_db),
    _auth=Depends(require_api_key),
    _rl=Depends(rate_limit_quiz)
):
    """Submit quiz answers and get results"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Calculate score
    questions = quiz.questions
    correct_count = 0
    incorrect_questions = []
    
    for question in questions:
        q_id = question["id"]
        correct_answer = question.get("correct_answer")
        user_answer = data.answers.get(q_id)
        
        if user_answer == correct_answer:
            correct_count += 1
        else:
            incorrect_questions.append(question)
    
    total = len(questions)
    
    # Get AI analysis
    analysis, knowledge_gaps = await analyze_quiz_results(
        correct_count, total, incorrect_questions
    )
    
    # Save attempt
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        answers=data.answers,
        score=correct_count,
        total=total,
        analysis=analysis,
        knowledge_gaps=knowledge_gaps
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    return QuizResultResponse(**attempt.to_dict())


@router.get("/{quiz_id}/results")
def get_quiz_results(quiz_id: str, db: Session = Depends(get_db)):
    """Get latest quiz attempt results"""
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id
    ).order_by(QuizAttempt.created_at.desc()).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="No quiz attempts found")
    
    return attempt.to_dict()
