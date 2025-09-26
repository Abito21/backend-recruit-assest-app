from celery import Celery
import asyncio
from datetime import datetime
# from typing import Dict, Any
from loguru import logger
from sqlmodel import Session
from app.config import settings
from app.database import engine
from app.models.evaluation import Evaluation, EvaluationStatus
from app.services.evaluation import EvaluationService

# Initialize Celery
celery_app = Celery(
    "ai_resume_evaluator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.celery_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,  # 1 hour
)

@celery_app.task(bind=True, name='evaluate_candidate')
def evaluate_candidate_task(
    self, 
    evaluation_id: str,
    cv_content: str, 
    project_content: str, 
    job_description: str
):
    """Background task to evaluate candidate CV and project"""
    
    logger.info(f"Starting evaluation task for {evaluation_id}")
    
    try:
        # Update status to processing
        with Session(engine) as session:
            evaluation = session.get(Evaluation, evaluation_id)
            if evaluation:
                evaluation.status = EvaluationStatus.PROCESSING
                evaluation.updated_at = datetime.now()
                session.add(evaluation)
                session.commit()
                logger.info(f"Updated {evaluation_id} status to PROCESSING")
        
        # Run evaluation (need to handle async in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            evaluation_service = EvaluationService()
            result = loop.run_until_complete(
                evaluation_service.evaluate_candidate(
                    cv_content=cv_content,
                    project_content=project_content,
                    job_description=job_description,
                    evaluation_id=evaluation_id
                )
            )
            
            # Save results to database
            with Session(engine) as session:
                evaluation = session.get(Evaluation, evaluation_id)
                if evaluation:
                    evaluation.status = EvaluationStatus.COMPLETED
                    evaluation.result = result.model_dump_json()
                    evaluation.cv_extraction = result.cv_extraction.model_dump_json()
                    evaluation.processing_time = (
                        datetime.now() - evaluation.created_at
                    ).total_seconds()
                    evaluation.updated_at = datetime.now()
                    session.add(evaluation)
                    session.commit()
                    
                    logger.success(f"Evaluation {evaluation_id} completed successfully")
                    
            return {
                "status": "completed",
                "evaluation_id": evaluation_id,
                "result": result.dict()
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Evaluation {evaluation_id} failed: {e}")
        
        # Update status to failed
        try:
            with Session(engine) as session:
                evaluation = session.get(Evaluation, evaluation_id)
                if evaluation:
                    evaluation.status = EvaluationStatus.FAILED
                    evaluation.error_message = str(e)
                    evaluation.updated_at = datetime.now()
                    session.add(evaluation)
                    session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")
        
        # Re-raise for Celery to handle
        raise self.retry(exc=e, countdown=60, max_retries=3)