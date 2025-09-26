import chromadb
# from chromadb.config import Settings
# import json
# from typing import Dict, Any, List
from loguru import logger
from app.config import settings
from app.models.evaluation import CVExtraction

class VectorStore:
    """ChromaDB integration for RAG implementation"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        self.job_collection = None
        self.rubric_collection = None
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialize ChromaDB collections"""
        try:
            # Collection for job descriptions
            self.job_collection = self.client.get_or_create_collection(
                name="job_descriptions",
                metadata={"description": "Job requirements and descriptions"}
            )
            
            # Collection for scoring rubrics
            self.rubric_collection = self.client.get_or_create_collection(
                name="scoring_rubrics", 
                metadata={"description": "Project evaluation rubrics"}
            )
            
            logger.info("ChromaDB collections initialized successfully")
            
            # Populate with default data if empty
            if self.job_collection.count() == 0:
                self._populate_default_data()
                
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _populate_default_data(self):
        """Populate collections with default job templates and rubrics"""
        logger.info("Populating ChromaDB with default data")
        
        # Default job requirements by category
        job_data = [
            {
                "id": "backend_dev",
                "category": "Backend",
                "content": """
                Backend Developer Requirements:
                - Strong proficiency in Python, Java, or Node.js
                - Experience with RESTful API design and development
                - Database design and optimization (PostgreSQL, MySQL, MongoDB)
                - Cloud platforms (AWS, GCP, Azure) and containerization (Docker)
                - Message queues and caching (Redis, RabbitMQ)
                - Version control with Git and CI/CD pipelines
                - Understanding of microservices architecture
                - 3+ years of backend development experience
                - Strong problem-solving and analytical skills
                """,
                "metadata": {"category": "Backend", "level": "mid-senior"}
            },
            {
                "id": "ai_ml_engineer", 
                "category": "AI/ML",
                "content": """
                AI/ML Engineer Requirements:
                - Proficiency in Python and ML libraries (TensorFlow, PyTorch, scikit-learn)
                - Understanding of machine learning algorithms and statistics
                - Experience with data preprocessing and feature engineering
                - Knowledge of MLOps, model deployment, and monitoring
                - Familiarity with vector databases (ChromaDB, Pinecone, Weaviate)
                - Experience with LLM integration (OpenAI, Anthropic, Mistral)
                - REST API development for ML services
                - 2+ years in ML/AI development
                - Experience with production ML systems
                - Understanding of prompt engineering and RAG systems
                """,
                "metadata": {"category": "AI/ML", "level": "mid"}
            },
            {
                "id": "fullstack_dev",
                "category": "Fullstack", 
                "content": """
                Full Stack Developer Requirements:
                Frontend: React.js/Vue.js, TypeScript/JavaScript, HTML5, CSS3, Tailwind CSS
                Backend: Node.js/Python, RESTful APIs, GraphQL, database management
                - State management (Redux, Zustand, Pinia)
                - Authentication and authorization systems
                - Modern development workflows and tools
                - 3+ years full stack development experience
                - User-focused mindset and design sensibility
                - Agile development experience
                """,
                "metadata": {"category": "Fullstack", "level": "mid-senior"}
            }
        ]
        
        # Add job data to collection
        for job in job_data:
            self.job_collection.add(
                ids=[job["id"]],
                documents=[job["content"]],
                metadatas=[job["metadata"]]
            )
        
        # Default scoring rubric
        rubric_data = [
            {
                "id": "project_rubric_v1",
                "content": """
                Project Evaluation Scoring Rubric (1-10 scale):

                1. Correctness (25% weight):
                - 9-10: Fully implements all requirements (prompt design, LLM chaining, RAG, error handling)
                - 7-8: Implements most requirements with minor gaps
                - 5-6: Implements basic requirements but missing key components
                - 3-4: Partially implements requirements with major gaps
                - 1-2: Minimal implementation, major requirements missing

                2. Code Quality (25% weight):
                - 9-10: Clean, modular, well-structured, comprehensive tests
                - 7-8: Well-organized code with good practices, some tests
                - 5-6: Adequate structure, follows basic best practices
                - 3-4: Poor organization, inconsistent patterns
                - 1-2: Messy, hard to understand code

                3. Resilience (25% weight):
                - 9-10: Comprehensive error handling, retries, graceful degradation
                - 7-8: Good error handling with retry mechanisms
                - 5-6: Basic error handling implemented
                - 3-4: Minimal error handling, may crash on failures
                - 1-2: No error handling, brittle system

                4. Documentation (15% weight):
                - 9-10: Excellent README, clear architecture docs, code comments
                - 7-8: Good documentation covering setup and usage
                - 5-6: Basic documentation with setup instructions
                - 3-4: Minimal documentation, unclear setup
                - 1-2: No or very poor documentation

                5. Creativity/Bonus (10% weight):
                - 9-10: Multiple innovative features (auth, deployment, monitoring, advanced UI)
                - 7-8: Some creative additions beyond requirements
                - 5-6: Minor improvements or enhancements
                - 3-4: Minimal additional features
                - 1-2: No additional features beyond requirements
                """,
                "metadata": {"version": "1.0", "type": "project_evaluation"}
            }
        ]
        
        # Add rubric to collection
        for rubric in rubric_data:
            self.rubric_collection.add(
                ids=[rubric["id"]],
                documents=[rubric["content"]], 
                metadatas=[rubric["metadata"]]
            )
        
        logger.success("Default data populated in ChromaDB")
    
    async def retrieve_job_context(
        self, 
        job_description: str, 
        cv_extraction: CVExtraction
    ) -> str:
        """Retrieve relevant job context based on CV category and custom job description"""
        try:
            # If we have a custom job description, use it
            if job_description and len(job_description.strip()) > 50:
                logger.info("Using custom job description for context")
                context = f"Custom Job Description:\n{job_description}"
            else:
                # Otherwise, retrieve from vector store based on CV category
                logger.info(f"Retrieving job context for category: {cv_extraction.category_job}")
                
                query = f"{cv_extraction.category_job} developer requirements skills experience"
                results = self.job_collection.query(
                    query_texts=[query],
                    n_results=2
                )
                
                if results['documents'] and results['documents'][0]:
                    context = "\n".join(results['documents'][0])
                    logger.success(f"Retrieved {len(results['documents'][0])} job context documents")
                else:
                    # Fallback to generic requirements
                    context = """
                    General Requirements:
                    - Relevant technical skills for the position
                    - Appropriate experience level
                    - Problem-solving abilities
                    - Communication and teamwork skills
                    - Continuous learning mindset
                    """
                    logger.warning("Using generic job context as fallback")
            
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving job context: {e}")
            return "Unable to retrieve specific job requirements"
    
    async def retrieve_scoring_rubric(self) -> str:
        """Retrieve project scoring rubric"""
        try:
            results = self.rubric_collection.query(
                query_texts=["project evaluation scoring rubric"],
                n_results=1
            )
            
            if results['documents'] and results['documents'][0]:
                rubric = results['documents'][0][0]
                logger.info("Retrieved project scoring rubric")
                return rubric
            else:
                logger.warning("No scoring rubric found, using default")
                return "Evaluate based on correctness, code quality, resilience, documentation, and creativity"
                
        except Exception as e:
            logger.error(f"Error retrieving scoring rubric: {e}")
            return "Standard evaluation criteria apply"