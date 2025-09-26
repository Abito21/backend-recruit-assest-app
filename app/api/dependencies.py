from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlmodel import Session
from app.database import get_session
from app.models.evaluation import Evaluation
from loguru import logger

# Optional: Authentication dependency (if needed)
security = HTTPBearer(auto_error=False)

async def get_current_user(token: Optional[str] = Depends(security)):
    """Optional authentication dependency"""
    # Implement your authentication logic here if needed
    # For now, we'll skip authentication
    return None

def get_evaluation_or_404(
    evaluation_id: str,
    session: Session = Depends(get_session)
) -> Evaluation:
    """Get evaluation by ID or raise 404"""
    evaluation = session.get(Evaluation, evaluation_id)
    if not evaluation:
        logger.warning(f"Evaluation not found: {evaluation_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found"
        )
    return evaluation

def validate_file_type(filename: str, allowed_extensions: set = {".pdf", ".docx", ".txt"}):
    """Validate file extension"""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    file_ext = filename.lower().split('.')[-1]
    if f".{file_ext}" not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{file_ext} not allowed. Supported: {', '.join(allowed_extensions)}"
        )
    
    return True