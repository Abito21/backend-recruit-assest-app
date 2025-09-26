# from typing import Dict, Any
# import asyncio
import time
from loguru import logger
from .ai_pipeline import AIPipeline
from .vector_store import VectorStore
from app.models.evaluation import EvaluationResult # , CVExtraction

class EvaluationService:
    """Main evaluation service orchestrating the AI pipeline"""
    
    def __init__(self):
        self.ai_pipeline = AIPipeline()
        self.vector_store = VectorStore()
    
    async def evaluate_candidate(
        self, 
        cv_content: str, 
        project_content: str, 
        job_description: str,
        evaluation_id: str
    ) -> EvaluationResult:
        """
        Main evaluation pipeline with 4 steps:
        1. Extract CV structure with detailed information
        2. Retrieve relevant job context via RAG
        3. Evaluate CV match rate with detailed scoring
        4. Evaluate project deliverables with rubric
        """
        
        start_time = time.time()
        
        try:
            # Step 1: Extract structured info from CV
            logger.info(f"[{evaluation_id}] Step 1: Extracting CV structure")
            cv_extraction = await self.ai_pipeline.extract_cv_structure(cv_content)
            
            logger.info(f"[{evaluation_id}] CV extraction completed - Found: {cv_extraction.email}, {cv_extraction.category_job}")
            
            # Step 2: Retrieve relevant job requirements via RAG
            logger.info(f"[{evaluation_id}] Step 2: Retrieving job context")
            job_context = await self.vector_store.retrieve_job_context(
                job_description, cv_extraction
            )
            
            # Step 3: CV matching and scoring
            logger.info(f"[{evaluation_id}] Step 3: Evaluating CV match")
            cv_evaluation = await self.ai_pipeline.evaluate_cv_match(
                cv_extraction, job_context
            )
            
            # Step 4: Project evaluation with scoring rubric
            logger.info(f"[{evaluation_id}] Step 4: Evaluating project deliverables")
            scoring_rubric = await self.vector_store.retrieve_scoring_rubric()
            project_evaluation = await self.ai_pipeline.evaluate_project(
                project_content, scoring_rubric
            )
            
            # Step 5: Generate overall summary
            logger.info(f"[{evaluation_id}] Step 5: Generating overall summary")
            overall_summary = await self.ai_pipeline.generate_summary(
                cv_evaluation, project_evaluation
            )
            
            # Compile detailed scores
            detailed_scores = {
                **cv_evaluation.get("skill_breakdown", {}),
                **project_evaluation.get("parameter_scores", {})
            }
            
            processing_time = time.time() - start_time
            
            result = EvaluationResult(
                cv_match_rate=cv_evaluation.get("match_rate", 0.0),
                cv_feedback=cv_evaluation.get("feedback", "No feedback available"),
                project_score=project_evaluation.get("score", 0.0),
                project_feedback=project_evaluation.get("feedback", "No feedback available"), 
                overall_summary=overall_summary,
                cv_extraction=cv_extraction.model_dump(),
                detailed_scores=detailed_scores
            )
            
            logger.success(f"[{evaluation_id}] Evaluation completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"[{evaluation_id}] Evaluation failed: {e}")
            raise Exception(f"Evaluation pipeline failed: {str(e)}")