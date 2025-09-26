from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
# from typing import Optional
import json
from loguru import logger
from app.models.evaluation import ResultResponse, Evaluation, EvaluationStatus, EvaluationResult
from app.database import get_session
# from app.api.dependencies import get_evaluation_or_404

router = APIRouter(tags=["results"])

@router.get("/result/{evaluation_id}", response_model=ResultResponse)
async def get_evaluation_result(
    evaluation_id: str,
    session: Session = Depends(get_session)
):
    """Get evaluation result by ID"""
    
    logger.info(f"Fetching result for evaluation: {evaluation_id}")
    
    try:
        # Get evaluation from database
        evaluation = session.get(Evaluation, evaluation_id)
        
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Prepare base response
        response_data = {
            "id": evaluation.id,
            "status": evaluation.status.value,
            "created_at": evaluation.created_at,
            "processing_time": evaluation.processing_time
        }
        
        # Add result if completed
        if evaluation.status == EvaluationStatus.COMPLETED and evaluation.result:
            logger.info(f"Returning completed result for {evaluation_id}")
            
            # Convert result dict to EvaluationResult model
            # result_data = evaluation.result.copy()
            result_data = (
                json.loads(evaluation.result)
                if isinstance(evaluation.result, str)
                else evaluation.result
            )
            
            # Ensure cv_extraction is properly structured
            # if evaluation.cv_extraction:
            #     result_data["cv_extraction"] = evaluation.cv_extraction

            if evaluation.cv_extraction:
                result_data["cv_extraction"] = (
                    json.loads(evaluation.cv_extraction)
                    if isinstance(evaluation.cv_extraction, str)
                    else evaluation.cv_extraction
                )
            
            response_data["result"] = EvaluationResult(**result_data)
            
        elif evaluation.status == EvaluationStatus.FAILED:
            logger.warning(f"Evaluation {evaluation_id} failed: {evaluation.error_message}")
            response_data["error"] = evaluation.error_message
            
        elif evaluation.status == EvaluationStatus.PROCESSING:
            logger.info(f"Evaluation {evaluation_id} still processing")
            
        else:  # QUEUED
            logger.info(f"Evaluation {evaluation_id} still queued")
        
        return ResultResponse(**response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching result for {evaluation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch result: {str(e)}")

@router.get("/result/{evaluation_id}/cv-extraction")
async def get_cv_extraction(
    evaluation_id: str,
    session: Session = Depends(get_session)
):
    """Get just the CV extraction data for preview"""
    
    try:
        evaluation = session.get(Evaluation, evaluation_id)
        
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        if not evaluation.cv_extraction:
            return {"message": "CV extraction not yet available"}
        
        return {
            "extraction": evaluation.cv_extraction,
            "status": evaluation.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching CV extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch CV extraction")

@router.delete("/result/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: str,
    session: Session = Depends(get_session)
):
    """Delete evaluation record"""
    
    try:
        evaluation = session.get(Evaluation, evaluation_id)
        
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        session.delete(evaluation)
        session.commit()
        
        logger.info(f"Deleted evaluation: {evaluation_id}")
        
        return {"message": "Evaluation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting evaluation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete evaluation")