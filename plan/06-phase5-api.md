# Phase 5: API Serving Layer

**Duration:** 3-4 hours
**Priority:** High - User-facing interface
**Dependencies:** Phase 2 (Data Layer)

---

## Objectives

1. Build FastAPI application structure
2. Implement company listing endpoint with filtering
3. Implement single company retrieval endpoint
4. Add health check and status endpoints
5. Configure OpenAPI/Swagger documentation
6. Add CORS and middleware
7. Test all endpoints

---

## Task Checklist

### 5.1 Implement FastAPI Application (`src/api/main.py`)

**Purpose:** REST API for querying enriched companies

**Implementation:**

```python
"""
FastAPI application for CommonForge Lead Scoring API.

Provides REST endpoints for querying enriched company data.
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import logging

from src.db import get_db, check_connection
from src.models import Company
from src.schemas import (
    CompanyEnriched,
    CompanyListResponse,
    HealthCheck,
)
from src.config import settings

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CommonForge Lead Scoring API",
    description="""
    AI-powered B2B lead scoring and enrichment platform.

    This API provides access to enriched company data including:
    - ICP fit scores (0-100)
    - Company segments (SMB/Mid-Market/Enterprise)
    - Primary use cases for AI automation
    - Risk flags and concerns
    - Personalized sales pitches

    Data is enriched using advanced LLM analysis of company websites
    and structured business information.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# Root endpoint
@app.get(
    "/",
    response_model=HealthCheck,
    tags=["Health"],
    summary="Root health check"
)
async def root():
    """
    Root endpoint returning basic service information.
    """
    return HealthCheck(
        status="healthy",
        service="commonforge-api",
        database=check_connection()
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["Health"],
    summary="Detailed health check"
)
async def health_check():
    """
    Comprehensive health check including database connectivity.
    """
    db_healthy = check_connection()

    return HealthCheck(
        status="healthy" if db_healthy else "unhealthy",
        service="commonforge-api",
        database=db_healthy
    )


# List companies endpoint
@app.get(
    "/companies",
    response_model=CompanyListResponse,
    tags=["Companies"],
    summary="List enriched companies",
    description="""
    Retrieve a list of enriched companies with optional filtering.

    **Filters:**
    - `min_score`: Minimum ICP fit score (0-100)
    - `country`: Filter by country name
    - `segment`: Filter by segment (SMB, Mid-Market, Enterprise)

    Returns only successfully enriched companies.
    """
)
async def list_companies(
    min_score: int = Query(
        0,
        ge=0,
        le=100,
        description="Minimum ICP fit score"
    ),
    country: Optional[str] = Query(
        None,
        max_length=100,
        description="Filter by country"
    ),
    segment: Optional[str] = Query(
        None,
        description="Filter by segment",
        regex="^(SMB|Mid-Market|Enterprise)$"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of results"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip"
    ),
    db: Session = Depends(get_db)
):
    """
    List enriched companies with filtering and pagination.
    """
    try:
        # Build query - only successfully enriched companies
        query = db.query(Company).filter(
            Company.enrichment_status == "success"
        )

        # Apply filters
        if min_score > 0:
            query = query.filter(Company.icp_fit_score >= min_score)

        if country:
            query = query.filter(
                func.lower(Company.country) == country.lower()
            )

        if segment:
            query = query.filter(Company.segment == segment)

        # Get total count
        total = query.count()

        # Apply sorting (highest score first)
        query = query.order_by(Company.icp_fit_score.desc())

        # Apply pagination
        companies = query.offset(offset).limit(limit).all()

        logger.info(
            f"Returned {len(companies)} companies "
            f"(total: {total}, min_score: {min_score})"
        )

        return CompanyListResponse(
            total=total,
            companies=companies
        )

    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Get single company endpoint
@app.get(
    "/companies/{company_id}",
    response_model=CompanyEnriched,
    tags=["Companies"],
    summary="Get company by ID",
    description="Retrieve detailed information for a specific company by ID."
)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a single company by ID.
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {company_id} not found"
            )

        logger.info(f"Retrieved company {company_id}: {company.company_name}")

        return company

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving company {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Get company by domain endpoint
@app.get(
    "/companies/by-domain/{domain}",
    response_model=CompanyEnriched,
    tags=["Companies"],
    summary="Get company by domain",
    description="Retrieve company information by domain name."
)
async def get_company_by_domain(
    domain: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a company by domain name.
    """
    try:
        # Normalize domain
        domain = domain.lower().strip()

        company = db.query(Company).filter(
            func.lower(Company.domain) == domain
        ).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with domain '{domain}' not found"
            )

        logger.info(f"Retrieved company by domain {domain}: {company.company_name}")

        return company

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving company by domain {domain}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Statistics endpoint
@app.get(
    "/stats",
    tags=["Statistics"],
    summary="Get database statistics",
    description="Get statistics about enriched companies in the database."
)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get statistics about the companies in the database.
    """
    try:
        total_companies = db.query(Company).count()

        enriched_companies = db.query(Company).filter(
            Company.enrichment_status == "success"
        ).count()

        avg_score = db.query(func.avg(Company.icp_fit_score)).filter(
            Company.enrichment_status == "success"
        ).scalar()

        segment_counts = db.query(
            Company.segment,
            func.count(Company.id)
        ).filter(
            Company.enrichment_status == "success"
        ).group_by(Company.segment).all()

        country_counts = db.query(
            Company.country,
            func.count(Company.id)
        ).filter(
            Company.enrichment_status == "success"
        ).group_by(Company.country).all()

        return {
            "total_companies": total_companies,
            "enriched_companies": enriched_companies,
            "average_icp_score": round(avg_score, 2) if avg_score else None,
            "by_segment": dict(segment_counts),
            "by_country": dict(country_counts),
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
```

---

### 5.2 Create API Test Suite (`tests/test_api.py`)

**Implementation:**

```python
"""
Tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from src.db import Base, get_db
from src.models import Company

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Set up test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_company():
    """Create a sample company for testing"""
    db = TestingSessionLocal()

    company = Company(
        company_name="Test Corp",
        domain="test.com",
        country="USA",
        employee_count=100,
        industry_raw="Technology",
        website_text_snippet="We are a test company",
        scraping_status="success",
        icp_fit_score=85,
        segment="Mid-Market",
        primary_use_case="AI automation for workflows",
        risk_flags=["Limited budget"],
        personalized_pitch="Test pitch",
        enrichment_status="success",
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    yield company

    db.delete(company)
    db.commit()
    db.close()


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_root(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "commonforge-api"

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data


class TestCompanyEndpoints:
    """Tests for company endpoints"""

    def test_list_companies_empty(self):
        """Test listing companies when database is empty"""
        response = client.get("/companies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["companies"] == []

    def test_list_companies_with_data(self, sample_company):
        """Test listing companies with data"""
        response = client.get("/companies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["companies"]) >= 1

    def test_list_companies_with_filters(self, sample_company):
        """Test filtering companies"""
        # Filter by min score
        response = client.get("/companies?min_score=80")
        assert response.status_code == 200
        data = response.json()
        assert all(c["icp_fit_score"] >= 80 for c in data["companies"])

        # Filter by segment
        response = client.get("/companies?segment=Mid-Market")
        assert response.status_code == 200
        data = response.json()
        assert all(c["segment"] == "Mid-Market" for c in data["companies"])

    def test_get_company_by_id(self, sample_company):
        """Test getting company by ID"""
        response = client.get(f"/companies/{sample_company.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Test Corp"
        assert data["domain"] == "test.com"

    def test_get_company_by_id_not_found(self):
        """Test getting non-existent company"""
        response = client.get("/companies/99999")
        assert response.status_code == 404

    def test_get_company_by_domain(self, sample_company):
        """Test getting company by domain"""
        response = client.get("/companies/by-domain/test.com")
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "test.com"

    def test_get_statistics(self, sample_company):
        """Test statistics endpoint"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_companies" in data
        assert "enriched_companies" in data
        assert "average_icp_score" in data
```

**Run tests:**
```bash
pytest tests/test_api.py -v
```

---

### 5.3 Create API Usage Examples

**File:** `docs/api_examples.md`

```markdown
# API Usage Examples

## Authentication
Currently no authentication required (add for production).

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "commonforge-api",
  "database": true
}
```

### 2. List All Companies
```bash
curl http://localhost:8000/companies
```

**Response:**
```json
{
  "total": 5,
  "companies": [
    {
      "id": 1,
      "company_name": "HubSpot",
      "domain": "hubspot.com",
      "country": "USA",
      "employee_count": 7400,
      "industry_raw": "Marketing & CRM Software",
      "website_text_snippet": "HubSpot provides...",
      "icp_fit_score": 91,
      "segment": "Enterprise",
      "primary_use_case": "AI-powered marketing automation",
      "risk_flags": ["Complex enterprise stack"],
      "personalized_pitch": "HubSpot could leverage...",
      "enrichment_status": "success",
      "created_at": "2025-01-11T10:30:00Z"
    }
  ]
}
```

### 3. Filter by Score
```bash
curl "http://localhost:8000/companies?min_score=80"
```

### 4. Filter by Segment
```bash
curl "http://localhost:8000/companies?segment=Enterprise"
```

### 5. Multiple Filters
```bash
curl "http://localhost:8000/companies?min_score=70&segment=Mid-Market&country=USA"
```

### 6. Get Specific Company
```bash
curl http://localhost:8000/companies/1
```

### 7. Get Company by Domain
```bash
curl http://localhost:8000/companies/by-domain/hubspot.com
```

### 8. Get Statistics
```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "total_companies": 5,
  "enriched_companies": 5,
  "average_icp_score": 82.4,
  "by_segment": {
    "SMB": 1,
    "Mid-Market": 3,
    "Enterprise": 1
  },
  "by_country": {
    "USA": 4,
    "Israel": 1
  }
}
```
```

---

## Verification Steps

### 5.4 Start API Server

```bash
# Start server in development mode
uvicorn src.api.main:app --reload

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

### 5.5 Test Endpoints

```bash
# Test health check
curl http://localhost:8000/health

# Test API docs
open http://localhost:8000/docs  # macOS
# or xdg-open http://localhost:8000/docs  # Linux
```

### 5.6 Run API Tests

```bash
pytest tests/test_api.py -v
```

---

## OpenAPI Documentation

Access interactive API documentation:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Success Criteria

After completing Phase 5, you should have:

- ✅ Working FastAPI application
- ✅ All CRUD endpoints functional
- ✅ Filtering and pagination working
- ✅ OpenAPI documentation generated
- ✅ All API tests passing
- ✅ Health check endpoints responding

---

## Next Steps

Once Phase 5 is complete:
1. Verify all endpoints work correctly
2. Test with enriched data from Phase 4
3. Proceed to **Phase 6: Pipeline Orchestration**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Implement main.py | 90 min |
| Create test suite | 60 min |
| Write API documentation | 30 min |
| Testing and debugging | 45 min |
| **Total** | **3.5 hours** |
