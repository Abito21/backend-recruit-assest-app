from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from loguru import logger
from app.models.evaluation import EvaluateRequest, EvaluateResponse, Evaluation, EvaluationStatus, JobTemplate
from app.tasks.celery_tasks import evaluate_candidate_task
from app.database import get_session
import uuid

router = APIRouter(tags=["evaluation"])

@router.post("/evaluate", response_model=EvaluateResponse)
async def start_evaluation(
    request: EvaluateRequest,
    session: Session = Depends(get_session)
):
    """Start evaluation process (async background task)"""
    
    logger.info("Received evaluation request")
    
    try:
        # Generate unique evaluation ID
        evaluation_id = str(uuid.uuid4())
        
        # Get job description (either custom or from template)
        job_description = ""
        
        if request.job_template_id:
            # Use job template
            job_template = session.get(JobTemplate, str(request.job_template_id))
            if job_template:
                job_description = f"{job_template.description}\n\nRequirements:\n{job_template.requirements}"
                logger.info(f"Using job template: {job_template.title}")
            else:
                raise HTTPException(status_code=404, detail="Job template not found")
        elif request.job_description:
            # Use custom job description
            job_description = request.job_description
            logger.info("Using custom job description")
        else:
            raise HTTPException(status_code=400, detail="Either job_template_id or job_description must be provided")
        
        # Validate input lengths
        if len(request.cv_content.strip()) < 50:
            raise HTTPException(status_code=400, detail="CV content too short")
        
        if len(request.project_content.strip()) < 50:
            raise HTTPException(status_code=400, detail="Project content too short")
        
        # Create evaluation record in database
        evaluation = Evaluation(
            id=evaluation_id,
            cv_content=request.cv_content,
            project_content=request.project_content,
            job_description=job_description,
            job_template_id=request.job_template_id,
            status=EvaluationStatus.QUEUED
        )
        
        session.add(evaluation)
        session.commit()
        
        logger.info(f"Created evaluation record: {evaluation_id}")
        
        # Queue background task
        task = evaluate_candidate_task.delay(
            evaluation_id=evaluation_id,
            cv_content=request.cv_content,
            project_content=request.project_content,
            job_description=job_description
        )
        
        logger.info(f"Queued evaluation task: {task.id}")
        
        return EvaluateResponse(
            id=evaluation_id,
            status="queued"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error starting evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start evaluation: {str(e)}")