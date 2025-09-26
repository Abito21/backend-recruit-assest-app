import openai
from typing import Dict, Any # , List, Optional
import json
import asyncio
import time
from loguru import logger
from langfuse import Langfuse, observe
from app.config import settings
from app.models.evaluation import CVExtraction

class AIPipeline:
    def __init__(self):
        self.client = openai.AsyncClient(api_key=settings.OPENAI_API_KEY)
        self.max_retries = 3
        self.base_delay = 1
        
        # Initialize Langfuse for LLM observability
        if all([settings.LANGFUSE_SECRET_KEY, settings.LANGFUSE_PUBLIC_KEY]):
            self.langfuse = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST
            )
            logger.info("Langfuse initialized for LLM observability")
        else:
            self.langfuse = None
            logger.warning("Langfuse not configured - LLM calls won't be tracked")
    
    @observe(name="extract_cv_structure")
    async def extract_cv_structure(self, cv_content: str) -> CVExtraction:
        """Step 1: Extract structured information from CV"""
        logger.info("Starting CV structure extraction")
        
        prompt = f"""
        Analyze this CV and extract structured information in JSON format.
        Be thorough and accurate in extracting all available information.

        CV Content:
        {cv_content}

        Extract the following information and return as valid JSON:
        {{
            "email": "candidate email address",
            "phone": "phone number with country code if available",
            "address": "full address or city/country",
            "category_job": "primary job category/role (e.g., Backend Developer, AI Engineer, Full Stack Developer)",
            "summary": "professional summary or objective (2-3 sentences max)",
            "skills": ["list", "of", "technical", "skills"],
            "strengths": ["key", "professional", "strengths", "and", "achievements"],
            "experience_years": estimated_total_years_of_experience_as_integer,
            "education": [
                {{
                    "degree": "degree name",
                    "institution": "university/school name", 
                    "year": "graduation year or period"
                }}
            ],
            "certifications": ["list", "of", "certifications"],
            "projects": [
                {{
                    "name": "project name",
                    "description": "brief description",
                    "technologies": ["tech1", "tech2"]
                }}
            ]
        }}

        Guidelines:
        - If information is not available, use null or empty array []
        - Skills should be specific technical skills, not soft skills
        - Strengths should focus on professional achievements and capabilities
        - Experience years should be your best estimate based on career progression
        - Only return valid JSON, no additional text
        """
        
        raw_result = await self._call_llm_with_retry(prompt, "cv_extraction")
        
        try:
            # Parse and validate the extraction
            cv_extraction = CVExtraction(**raw_result)
            
            logger.success(f"Successfully extracted CV structure: {cv_extraction.category_job} with {cv_extraction.experience_years} years experience")
            return cv_extraction
            
        except Exception as e:
            logger.error(f"Failed to parse CV extraction result: {e}")
            # Return minimal valid structure
            return CVExtraction(
                summary="Failed to extract CV information",
                category_job="Unknown"
            )
    
    @observe(name="evaluate_cv_match")
    async def evaluate_cv_match(
        self, 
        cv_extraction: CVExtraction, 
        job_context: str
    ) -> Dict[str, Any]:
        """Step 2 & 3: Compare CV with job requirements"""
        logger.info(f"Evaluating CV match for {cv_extraction.category_job} position")
        
        prompt = f"""
        You are an expert HR evaluator. Compare this candidate profile with job requirements.

        Job Requirements:
        {job_context}

        Candidate Profile:
        - Position: {cv_extraction.category_job}
        - Experience: {cv_extraction.experience_years} years
        - Skills: {', '.join(cv_extraction.skills)}
        - Summary: {cv_extraction.summary}
        - Strengths: {', '.join(cv_extraction.strengths)}
        - Projects: {len(cv_extraction.projects)} relevant projects
        - Education: {len(cv_extraction.education)} qualifications

        Evaluate match rate (0.0-1.0) based on these weighted criteria:
        1. Technical Skills Match (40%) - How well do candidate's skills align with requirements?
        2. Experience Level (30%) - Does experience level meet job requirements?
        3. Relevant Achievements (20%) - Quality of projects and accomplishments
        4. Cultural Fit (10%) - Communication, learning attitude indicators

        Return JSON format:
        {{
            "match_rate": 0.75,
            "feedback": "Detailed feedback highlighting strengths and gaps (3-4 sentences)",
            "skill_breakdown": {{
                "technical_skills": 0.8,
                "experience_level": 0.7,
                "achievements": 0.9,
                "cultural_fit": 0.6
            }},
            "missing_skills": ["skill1", "skill2"],
            "strong_points": ["strength1", "strength2"]
        }}

        Be honest and specific in your evaluation.
        """
        
        result = await self._call_llm_with_retry(prompt, "cv_evaluation")
        
        logger.info(f"CV evaluation completed with match rate: {result.get('match_rate', 'unknown')}")
        return result
    
    @observe(name="evaluate_project") 
    async def evaluate_project(
        self, 
        project_content: str, 
        scoring_rubric: str
    ) -> Dict[str, Any]:
        """Step 4: Evaluate project deliverables with two-step refinement"""
        logger.info("Starting project evaluation")
        
        # First evaluation pass
        initial_prompt = f"""
        Evaluate this project report against the scoring rubric.

        Scoring Rubric:
        {scoring_rubric}

        Project Report:
        {project_content}

        Score each parameter (1-10) and provide specific feedback:
        
        1. Correctness (25%) - Does it meet all requirements? (prompt design, LLM chaining, RAG, error handling)
        2. Code Quality (25%) - Is code clean, modular, well-structured, testable?
        3. Resilience (25%) - How well does it handle failures, implement retries, manage errors?
        4. Documentation (15%) - Quality of README, code comments, architecture explanation
        5. Creativity (10%) - Bonus features like authentication, deployment, monitoring, UI improvements

        Return JSON:
        {{
            "parameter_scores": {{
                "correctness": 8.0,
                "code_quality": 7.5,
                "resilience": 6.0,
                "documentation": 9.0,
                "creativity": 7.0
            }},
            "weighted_score": 7.4,
            "feedback": "Detailed feedback on each parameter (4-5 sentences)",
            "recommendations": ["specific improvement suggestion 1", "suggestion 2"]
        }}
        """
        
        initial_result = await self._call_llm_with_retry(initial_prompt, "project_initial_eval")
        
        # Calculate final score based on weights
        scores = initial_result.get("parameter_scores", {})
        final_score = (
            scores.get("correctness", 0) * 0.25 +
            scores.get("code_quality", 0) * 0.25 +
            scores.get("resilience", 0) * 0.25 +
            scores.get("documentation", 0) * 0.15 +
            scores.get("creativity", 0) * 0.10
        )
        
        initial_result["score"] = round(final_score, 1)
        
        logger.success(f"Project evaluation completed with score: {final_score}")
        return initial_result
    
    @observe(name="generate_summary")
    async def generate_summary(
        self, 
        cv_evaluation: Dict[str, Any], 
        project_evaluation: Dict[str, Any]
    ) -> str:
        """Generate overall candidate summary"""
        logger.info("Generating overall candidate summary")
        
        prompt = f"""
        Create a concise overall summary of this candidate based on CV and project evaluations.

        CV Evaluation:
        - Match Rate: {cv_evaluation.get('match_rate', 0)}
        - Feedback: {cv_evaluation.get('feedback', '')}

        Project Evaluation:
        - Score: {project_evaluation.get('score', 0)}/10
        - Feedback: {project_evaluation.get('feedback', '')}

        Write a 2-3 sentence executive summary that:
        1. States overall candidate fit
        2. Highlights key strengths
        3. Mentions main development areas

        Be professional, balanced, and actionable.
        """
        
        summary = await self._call_llm_with_retry(prompt, "generate_summary", response_format="text")
        
        logger.info("Overall summary generated successfully")
        return summary
    
    async def _call_llm_with_retry(
        self, 
        prompt: str, 
        task_type: str,
        temperature: float = 0.3,
        response_format: str = "json"
    ) -> Dict[str, Any] | str:
        """Call LLM with retry logic, error handling, and Langfuse tracking"""
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # Prepare messages
                if response_format == "json":
                    system_message = "You are an expert HR evaluator. Always return valid JSON only, no additional text."
                else:
                    system_message = "You are an expert HR evaluator. Provide clear, professional responses."
                
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"} if response_format == "json" else None,
                    timeout=60  # Increased timeout
                )
                
                duration = time.time() - start_time
                content = response.choices[0].message.content

                # Log success
                logger.success(f"LLM call successful for {task_type} (took {duration:.2f}s)")

                if not content or not content.strip():
                    logger.error(f"Empty response from LLM for {task_type}")
                    return {"error": "Empty LLM response"}

                # Track with Langfuse if available
                # if self.langfuse:
                #     trace = self.langfuse.trace(
                #         name=task_type,
                #         input=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                #         output=content[:500] + "..." if len(content) > 500 else content,
                #         metadata={
                #             "model": "gpt-4-turbo-preview",
                #             "temperature": temperature,
                #             "duration": duration,
                #             "attempt": attempt + 1
                #         }
                #     )
                #     trace.end()

                # Parse JSON response if needed
                # if response_format == "json":
                #     return json.loads(content)
                # else:
                #     return content

                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON for {task_type}: {e}")
                        return {"error": "Invalid JSON format"}
                else:
                    return content
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error for {task_type} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_delay * (2 ** attempt))
                else:
                    logger.error(f"Failed to parse JSON after {self.max_retries} attempts")
                    if response_format == "json":
                        return {"error": "Failed to parse LLM response"}
                    else:
                        return "Failed to generate response"
                        
            except Exception as e:
                logger.warning(f"LLM call failed for {task_type} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_delay * (2 ** attempt))
                else:
                    logger.error(f"All LLM retries failed for {task_type}: {e}")
                    raise Exception(f"LLM service unavailable after {self.max_retries} attempts: {str(e)}")