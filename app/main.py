from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from sqlalchemy import text
from loguru import logger
from scalar_fastapi import get_scalar_api_reference

from app.config import settings
from app.database import create_db_and_tables, init_default_data
from app.utils.logger import setup_logger
from app.api.routes import upload, evaluate, result

# Setup logging
setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting AI Resume Evaluator API...")
    
    try:
        # Create database tables
        create_db_and_tables()
        
        # Initialize default data
        init_default_data()
        
        logger.success("Application startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Resume Evaluator API...")

# Create FastAPI app
app = FastAPI(
    title="AI Resume Evaluator",
    description="Backend service for evaluating CVs and project reports using AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")
app.include_router(result.router, prefix="/api")

# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AI Resume Evaluator API",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        from app.database import engine
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected"  # TODO: Add Redis check
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.get("/scalar", include_in_schema=False)
async def scalar():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )