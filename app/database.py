from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from loguru import logger

# Create database engine
engine = create_engine(
    settings.DB_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=300,     # Recycle connections every 5 minutes
)

def create_db_and_tables():
    """Create database tables"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.success("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def get_session():
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session

# Initialize default job templates data
DEFAULT_JOB_TEMPLATES = [
    {
        "title": "Backend Developer",
        "category": "Backend",
        "description": "We are looking for a skilled Backend Developer to join our team. You will be responsible for server-side web application logic and integration of the work front-end developers do.",
        "requirements": """
Technical Skills Required:
- Proficiency in Python, Java, or Node.js
- Experience with RESTful API development
- Database design and optimization (PostgreSQL, MySQL)
- Cloud platforms (AWS, GCP, Azure)
- Docker and containerization
- Message queues (Redis, RabbitMQ)
- Version control with Git

Experience Level:
- 3+ years of backend development experience
- Experience with microservices architecture
- Understanding of system design principles

Soft Skills:
- Strong problem-solving abilities
- Good communication skills
- Ability to work in agile teams
        """,
        "is_active": True
    },
    {
        "title": "AI/ML Engineer", 
        "category": "AI/ML",
        "description": "Join our AI team to build intelligent systems and machine learning models that power our products.",
        "requirements": """
Technical Skills Required:
- Python, TensorFlow/PyTorch
- Machine Learning algorithms and statistics
- Data preprocessing and feature engineering
- MLOps and model deployment
- Vector databases (ChromaDB, Pinecone)
- LLM integration (OpenAI, Mistral, Claude)
- REST API development

Experience Level:
- 2+ years in ML/AI development
- Experience with production ML systems
- Understanding of prompt engineering

Soft Skills:
- Analytical thinking
- Continuous learning mindset
- Collaboration with cross-functional teams
        """,
        "is_active": True
    },
    {
        "title": "Full Stack Developer",
        "category": "Fullstack", 
        "description": "We need a versatile Full Stack Developer who can work on both frontend and backend systems.",
        "requirements": """
Technical Skills Required:
Frontend:
- React.js or Vue.js
- TypeScript/JavaScript
- HTML5, CSS3, Tailwind CSS
- State management (Redux, Zustand)

Backend:
- Node.js or Python
- RESTful APIs and GraphQL
- Database management
- Authentication systems

Experience Level:
- 3+ years full stack development
- Experience with modern development workflows

Soft Skills:
- Versatility and adaptability
- User-focused mindset
- Team collaboration
        """,
        "is_active": True
    }
]

def init_default_data():
    """Initialize database with default job templates"""
    from app.models.evaluation import JobTemplate
    
    try:
        with Session(engine) as session:
            # Check if we already have job templates
            existing_templates = session.query(JobTemplate).all()
            
            if len(existing_templates) == 0:
                logger.info("Initializing default job templates")
                
                for template_data in DEFAULT_JOB_TEMPLATES:
                    template = JobTemplate(**template_data)
                    session.add(template)
                
                session.commit()
                logger.success(f"Added {len(DEFAULT_JOB_TEMPLATES)} default job templates")
            else:
                logger.info(f"Database already has {len(existing_templates)} job templates")
                
    except Exception as e:
        logger.error(f"Failed to initialize default data: {e}")
        raise