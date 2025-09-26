from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from app.utils.generate_id import generate_id

class EvaluationStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class CVExtraction(SQLModel):
    """Structured CV data extraction"""
    id: str = Field(default_factory=generate_id, primary_key=True)
    fullname: Optional[str] = Field("")
    email: Optional[str] = Field("")
    phone: Optional[str] = Field("")
    address: Optional[str] = Field("")
    category_job: Optional[str] = Field("")
    summary: Optional[str] = Field("")
    skills: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    strengths: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    experience_years: Optional[int] = None
    education: List[Dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    certifications: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    projects: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = Field(default=False)

class JobTemplate(SQLModel, table=True):
    """Pre-defined job templates for easy selection"""
    id: Optional[str] = Field(default_factory=generate_id, primary_key=True)
    title: Optional[str] = Field("")
    category: Optional[str] = Field("")  # Backend, Frontend, Fullstack, AI/ML, etc.
    description: Optional[str] = Field("")
    requirements: Optional[str] = Field("")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

class Evaluation(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=generate_id, primary_key=True)
    status: EvaluationStatus = Field(default=EvaluationStatus.QUEUED)
    
    # Input data
    cv_content: Optional[str] = Field("")
    project_content: Optional[str] = Field("")
    job_description: Optional[str] = Field("")
    job_template_id: Optional[str] = Field(default="", foreign_key="jobtemplate.id")
    
    # Extracted data
    cv_extraction: Optional[CVExtraction] = Field(default=None, sa_column=Column(JSON))
    
    # Results
    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    # Metadata
    langfuse_trace_id: Optional[str] = Field("")
    processing_time: Optional[float] = None
    error_message: Optional[str] = Field("")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

# Pydantic schemas for API requests/responses
class EvaluateRequest(SQLModel):
    cv_content: Optional[str] = Field("")
    project_content: Optional[str] = Field("")
    job_description: Optional[str] = Field("")
    job_template_id: Optional[str] = Field("")

class EvaluateResponse(SQLModel):
    id: str
    status: Optional[str] = Field("")

class EvaluationResult(SQLModel):
    cv_match_rate: Optional[float] = None
    cv_feedback: Optional[str] = Field("")
    project_score: Optional[float] = None
    project_feedback: Optional[str] = Field("")
    overall_summary: Optional[str] = Field("")
    cv_extraction: Optional[CVExtraction] = Field(default=None, sa_column=Column(JSON))
    detailed_scores: Dict[str, float] = Field(default_factory=dict, sa_column=Column(JSON))

class ResultResponse(SQLModel):
    id: str
    status: Optional[str] = Field("")
    result: Optional[EvaluationResult] = None
    processing_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None

class UploadResponse(SQLModel):
    message: Optional[str] = Field("")
    cv_preview: Optional[str] = Field("")
    project_preview: Optional[str] = Field("")
    cv_length: Optional[int] = None
    project_length: Optional[int] = None
    available_job_templates: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))