from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Dict, Any
from loguru import logger
from app.services.file_processor import FileProcessor
from app.models.evaluation import JobTemplate, UploadResponse
from sqlmodel import Session, select
from app.database import get_session
from app.api.dependencies import validate_file_type

router = APIRouter(tags=["upload"])
file_processor = FileProcessor()

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    cv_file: UploadFile = File(..., description="CV file (PDF, DOCX, or TXT)"),
    project_file: UploadFile = File(..., description="Project report file"),
    session: Session = Depends(get_session)
):
    """Upload and process CV and project files"""
    
    logger.info(f"Upload request - CV: {cv_file.filename}, Project: {project_file.filename}")
    
    try:
        # Validate file types
        validate_file_type(cv_file.filename)
        validate_file_type(project_file.filename)
        
        # Process CV file
        logger.info("Processing CV file")
        cv_content = await file_processor.extract_text(cv_file)
        
        # Process project file  
        logger.info("Processing project file")
        project_content = await file_processor.extract_text(project_file)
        
        # Get available job templates for selection
        job_templates = session.exec(select(JobTemplate).where(JobTemplate.is_active == True)).all()
        
        response = UploadResponse(
            message="Files uploaded and processed successfully",
            cv_preview=cv_content[:300] + "..." if len(cv_content) > 300 else cv_content,
            project_preview=project_content[:300] + "..." if len(project_content) > 300 else project_content,
            cv_length=len(cv_content),
            project_length=len(project_content),
            available_job_templates=[
                {
                    "id": template.id,
                    "title": template.title,
                    "category": template.category
                }
                for template in job_templates
            ]
        )
        
        logger.success("File upload completed successfully")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (from file processor)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")

@router.get("/job-templates", response_model=List[Dict[str, Any]])
async def get_job_templates(session: Session = Depends(get_session)):
    """Get all available job templates"""
    
    try:
        templates = session.exec(select(JobTemplate).where(JobTemplate.is_active == True)).all()
        
        return [
            {
                "id": template.id,
                "title": template.title, 
                "category": template.category,
                "description": template.description[:200] + "..." if len(template.description) > 200 else template.description
            }
            for template in templates
        ]
        
    except Exception as e:
        logger.error(f"Error fetching job templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job templates")

@router.get("/job-templates/{template_id}", response_model=Dict[str, Any])
async def get_job_template(
    template_id: str,
    session: Session = Depends(get_session)
):
    """Get specific job template details"""
    
    try:
        template = session.get(JobTemplate, template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Job template not found")
        
        return {
            "id": template.id,
            "title": template.title,
            "category": template.category, 
            "description": template.description,
            "requirements": template.requirements
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job template")