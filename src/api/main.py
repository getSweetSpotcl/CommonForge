"""
FastAPI REST API for CommonForge lead scoring system.

Provides endpoints to query enriched company data.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict
import logging
import time
import uuid
import tempfile
import os
from pathlib import Path
import asyncio

from src.db import get_db, check_connection, engine
from src.models import Company
from src.schemas import CompanyEnriched, CompanyListResponse, HealthCheck
from src.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Job tracking (in-memory store)
# For production, use Redis
jobs: Dict[str, Dict] = {}

# Initialize FastAPI app
app = FastAPI(
    title="CommonForge API",
    description="AI-Powered B2B Lead Scoring System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )

    return response


# Mount static files for frontend (must be after API routes)
# Will be mounted at the end of file

# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - basic health check"""
    return {"service": "CommonForge API", "version": "1.0.0", "status": "healthy", "docs": "/docs"}


# Detailed health check
@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Detailed health check endpoint.

    Checks:
    - API status
    - Database connection
    - Database statistics
    """
    # Check database connection
    db_healthy = check_connection()

    # Get database stats
    try:
        total_companies = db.query(func.count(Company.id)).scalar()
        enriched_companies = (
            db.query(func.count(Company.id)).filter(Company.enrichment_status == "success").scalar()
        )
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        total_companies = 0
        enriched_companies = 0
        db_healthy = False

    # Overall health
    healthy = db_healthy

    return HealthCheck(
        status="healthy" if healthy else "unhealthy",
        database_connected=db_healthy,
        total_companies=total_companies,
        enriched_companies=enriched_companies,
    )


# List companies with filtering
@app.get("/companies", response_model=CompanyListResponse, tags=["Companies"])
async def list_companies(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    country: Optional[str] = Query(None, description="Filter by country"),
    segment: Optional[str] = Query(
        None, description="Filter by segment (SMB, Mid-Market, Enterprise)"
    ),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum ICP fit score"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum ICP fit score"),
    enriched_only: bool = Query(False, description="Return only enriched companies"),
    sort_by: str = Query(
        "icp_fit_score", description="Sort field (icp_fit_score, company_name, employee_count)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    db: Session = Depends(get_db),
):
    """
    List companies with optional filtering and pagination.

    **Filters:**
    - `country`: Filter by country name
    - `segment`: Filter by segment (SMB, Mid-Market, Enterprise)
    - `min_score`, `max_score`: Filter by ICP fit score range
    - `enriched_only`: Only return successfully enriched companies

    **Pagination:**
    - `skip`: Number of records to skip (default: 0)
    - `limit`: Maximum records to return (default: 100, max: 1000)

    **Sorting:**
    - `sort_by`: Field to sort by (default: icp_fit_score)
    - `sort_order`: asc or desc (default: desc)
    """
    try:
        # Build query
        query = db.query(Company)

        # Apply filters
        if country:
            query = query.filter(Company.country == country)

        if segment:
            query = query.filter(Company.segment == segment)

        if min_score is not None:
            query = query.filter(Company.icp_fit_score >= min_score)

        if max_score is not None:
            query = query.filter(Company.icp_fit_score <= max_score)

        if enriched_only:
            query = query.filter(Company.enrichment_status == "success")

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_field = getattr(Company, sort_by, Company.icp_fit_score)
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)

        # Apply pagination
        companies = query.offset(skip).limit(limit).all()

        return CompanyListResponse(
            total=total,
            skip=skip,
            limit=limit,
            companies=[CompanyEnriched.model_validate(c) for c in companies],
        )

    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list companies: {str(e)}")


# Get single company by ID
@app.get("/companies/{company_id}", response_model=CompanyEnriched, tags=["Companies"])
async def get_company(company_id: int, db: Session = Depends(get_db)):
    """
    Get a single company by ID.

    **Parameters:**
    - `company_id`: Company ID

    **Returns:**
    - Complete company data with enrichment
    """
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")

    return CompanyEnriched.model_validate(company)


# Get company by domain
@app.get("/companies/by-domain/{domain}", response_model=CompanyEnriched, tags=["Companies"])
async def get_company_by_domain(domain: str, db: Session = Depends(get_db)):
    """
    Get a company by domain name.

    **Parameters:**
    - `domain`: Company domain (e.g., 'example.com')

    **Returns:**
    - Complete company data with enrichment
    """
    company = db.query(Company).filter(Company.domain == domain).first()

    if not company:
        raise HTTPException(status_code=404, detail=f"Company with domain '{domain}' not found")

    return CompanyEnriched.model_validate(company)


# Upload CSV and trigger pipeline
@app.post("/api/upload", tags=["Pipeline"])
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload CSV file and trigger pipeline processing.

    **Parameters:**
    - `file`: CSV file with company data

    **Returns:**
    - `job_id`: Unique job identifier for tracking progress
    - `status`: Initial job status
    - `message`: Status message
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{job_id}.csv")

        # Save uploaded file
        with open(temp_file_path, 'wb') as f:
            content = await file.read()
            f.write(content)

        # Initialize job tracking
        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": {
                "step": "Initializing",
                "current": 0,
                "total": 100,
                "message": "Pipeline queued"
            },
            "result": None,
            "error": None,
            "filename": file.filename
        }

        # Start pipeline in background
        background_tasks.add_task(run_pipeline_task, job_id, temp_file_path)

        logger.info(f"Upload successful - Job ID: {job_id}, File: {file.filename}")

        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"File '{file.filename}' uploaded successfully. Processing started."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Get job status
@app.get("/api/jobs/{job_id}", tags=["Pipeline"])
async def get_job_status(job_id: str):
    """
    Get status of a pipeline job.

    **Parameters:**
    - `job_id`: Job identifier from upload response

    **Returns:**
    - `job_id`: Job identifier
    - `status`: Current status (queued, processing, completed, failed)
    - `progress`: Progress information
    - `result`: Results (when completed)
    - `error`: Error message (if failed)
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return jobs[job_id]


# Statistics endpoint
@app.get("/stats", tags=["Statistics"])
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get system statistics.

    **Returns:**
    - Total companies
    - Enriched companies
    - Companies by segment
    - Companies by country
    - Average ICP score
    - Top companies by score
    """
    try:
        # Overall stats
        total = db.query(func.count(Company.id)).scalar()
        enriched = (
            db.query(func.count(Company.id)).filter(Company.enrichment_status == "success").scalar()
        )

        # Average score
        avg_score = (
            db.query(func.avg(Company.icp_fit_score))
            .filter(Company.icp_fit_score.isnot(None))
            .scalar()
        )

        # By segment
        segments = (
            db.query(Company.segment, func.count(Company.id).label("count"))
            .filter(Company.segment.isnot(None))
            .group_by(Company.segment)
            .all()
        )

        # By country
        countries = (
            db.query(Company.country, func.count(Company.id).label("count"))
            .group_by(Company.country)
            .all()
        )

        # Top companies by score
        top_companies = (
            db.query(Company)
            .filter(Company.icp_fit_score.isnot(None))
            .order_by(desc(Company.icp_fit_score))
            .limit(10)
            .all()
        )

        return {
            "total_companies": total,
            "enriched_companies": enriched,
            "enrichment_rate": f"{(enriched / total * 100):.1f}%" if total > 0 else "0%",
            "average_icp_score": round(float(avg_score), 2) if avg_score else None,
            "by_segment": {s.segment: s.count for s in segments},
            "by_country": {c.country: c.count for c in countries},
            "top_companies": [
                {
                    "id": c.id,
                    "company_name": c.company_name,
                    "domain": c.domain,
                    "icp_fit_score": c.icp_fit_score,
                    "segment": c.segment,
                }
                for c in top_companies
            ],
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error", "error": str(exc)}
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 60)
    logger.info("CommonForge API Starting")
    logger.info("=" * 60)
    logger.info(
        f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}"
    )
    logger.info(f"Docs: /docs")
    logger.info(f"Health: /health")
    logger.info("=" * 60)

    # Check database connection
    if check_connection():
        logger.info("✓ Database connection successful")
    else:
        logger.error("✗ Database connection failed")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information"""
    logger.info("CommonForge API shutting down...")
    engine.dispose()


# Background task to run pipeline
async def run_pipeline_task(job_id: str, csv_path: str):
    """
    Run pipeline as background task with progress tracking.

    Args:
        job_id: Job identifier
        csv_path: Path to CSV file
    """
    from src.pipeline import Pipeline

    try:
        # Update status to processing
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"]["message"] = "Starting pipeline..."

        def progress_callback(step: str, current: int, total: int, message: str):
            """Callback to update job progress"""
            jobs[job_id]["progress"] = {
                "step": step,
                "current": current,
                "total": total,
                "message": message
            }

        # Create pipeline with progress callback
        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=False,
            skip_scraping=False,
            skip_enrichment=False,
            max_companies=None
        )

        # Add progress tracking manually for each step
        jobs[job_id]["progress"] = {
            "step": "Loading CSV",
            "current": 10,
            "total": 100,
            "message": "Loading company data..."
        }

        # Run pipeline
        success = await pipeline.run()

        if success:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = {
                "step": "Completed",
                "current": 100,
                "total": 100,
                "message": "Pipeline completed successfully"
            }
            jobs[job_id]["result"] = {
                "companies_processed": pipeline.stats["csv_loaded"],
                "websites_scraped": pipeline.stats["websites_scraped"],
                "scraping_successful": pipeline.stats["scraping_successful"],
                "companies_enriched": pipeline.stats["companies_enriched"],
                "enrichment_successful": pipeline.stats["enrichment_successful"],
                "companies_persisted": pipeline.stats["companies_persisted"]
            }
            logger.info(f"Job {job_id} completed successfully")
        else:
            raise Exception("Pipeline returned failure status")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["progress"]["message"] = f"Error: {str(e)}"

    finally:
        # Clean up temporary file
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
        except Exception as e:
            logger.warning(f"Failed to remove temp file {csv_path}: {e}")


# Mount static files for frontend (must be last to not interfere with API routes)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"Frontend mounted at /app from {frontend_path}")
else:
    logger.warning(f"Frontend directory not found at {frontend_path}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
