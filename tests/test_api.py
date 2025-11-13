"""
Tests for FastAPI REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.db import Base, get_db
from src.models import Company

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_companies():
    """Create sample companies for testing"""
    db = TestingSessionLocal()

    companies = [
        Company(
            company_name="HubSpot",
            domain="hubspot.com",
            country="USA",
            employee_count=7000,
            industry_raw="Sales & Marketing SaaS",
            website_text_snippet="Inbound marketing and sales software",
            scraping_status="success",
            icp_fit_score=95,
            segment="Enterprise",
            primary_use_case="Sales automation",
            risk_flags=[],
            personalized_pitch="Perfect fit for enterprise sales teams",
            enrichment_status="success"
        ),
        Company(
            company_name="Asana",
            domain="asana.com",
            country="USA",
            employee_count=1500,
            industry_raw="Project Management SaaS",
            website_text_snippet="Work management platform",
            scraping_status="success",
            icp_fit_score=80,
            segment="Mid-Market",
            primary_use_case="Team collaboration",
            risk_flags=["Budget concerns"],
            personalized_pitch="Great for growing teams",
            enrichment_status="success"
        ),
        Company(
            company_name="Small Corp",
            domain="smallcorp.com",
            country="Canada",
            employee_count=50,
            industry_raw="Consulting",
            website_text_snippet="Consulting services",
            scraping_status="success",
            icp_fit_score=40,
            segment="SMB",
            primary_use_case="Client management",
            risk_flags=["Non-tech industry"],
            personalized_pitch="Consider for SMB segment",
            enrichment_status="success"
        ),
        Company(
            company_name="Failed Corp",
            domain="failed.com",
            country="USA",
            employee_count=100,
            industry_raw="Unknown",
            website_text_snippet=None,
            scraping_status="failed",
            enrichment_status="skipped",
            enrichment_error="Skipped due to scraping failure"
        )
    ]

    for company in companies:
        db.add(company)

    db.commit()
    db.close()

    return companies


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "CommonForge API"
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_endpoint(self, sample_companies):
        """Test detailed health check"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["total_companies"] == 4
        assert data["enriched_companies"] == 3


class TestCompanyEndpoints:
    """Tests for company endpoints"""

    def test_list_companies_default(self, sample_companies):
        """Test listing companies with default parameters"""
        response = client.get("/companies")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 4
        assert data["skip"] == 0
        assert data["limit"] == 100
        assert len(data["companies"]) == 4

    def test_list_companies_pagination(self, sample_companies):
        """Test pagination"""
        response = client.get("/companies?skip=1&limit=2")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 4
        assert data["skip"] == 1
        assert data["limit"] == 2
        assert len(data["companies"]) == 2

    def test_list_companies_filter_by_country(self, sample_companies):
        """Test filtering by country"""
        response = client.get("/companies?country=USA")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert all(c["country"] == "USA" for c in data["companies"])

    def test_list_companies_filter_by_segment(self, sample_companies):
        """Test filtering by segment"""
        response = client.get("/companies?segment=Mid-Market")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["companies"][0]["segment"] == "Mid-Market"
        assert data["companies"][0]["company_name"] == "Asana"

    def test_list_companies_filter_by_score_range(self, sample_companies):
        """Test filtering by ICP score range"""
        response = client.get("/companies?min_score=70&max_score=90")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["companies"][0]["icp_fit_score"] == 80

    def test_list_companies_enriched_only(self, sample_companies):
        """Test filtering enriched companies only"""
        response = client.get("/companies?enriched_only=true")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert all(c["enrichment_status"] == "success" for c in data["companies"])

    def test_list_companies_sort_by_name(self, sample_companies):
        """Test sorting by company name"""
        response = client.get("/companies?sort_by=company_name&sort_order=asc")
        assert response.status_code == 200

        data = response.json()
        names = [c["company_name"] for c in data["companies"]]
        assert names == sorted(names)

    def test_list_companies_sort_by_score_desc(self, sample_companies):
        """Test sorting by score descending (default)"""
        response = client.get("/companies?enriched_only=true")
        assert response.status_code == 200

        data = response.json()
        scores = [c["icp_fit_score"] for c in data["companies"]]
        assert scores == sorted(scores, reverse=True)

    def test_get_company_by_id_success(self, sample_companies):
        """Test getting single company by ID"""
        response = client.get("/companies/1")
        assert response.status_code == 200

        data = response.json()
        assert data["company_name"] == "HubSpot"
        assert data["domain"] == "hubspot.com"
        assert data["icp_fit_score"] == 95

    def test_get_company_by_id_not_found(self, sample_companies):
        """Test getting non-existent company"""
        response = client.get("/companies/999")
        assert response.status_code == 404

        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_company_by_domain_success(self, sample_companies):
        """Test getting company by domain"""
        response = client.get("/companies/by-domain/asana.com")
        assert response.status_code == 200

        data = response.json()
        assert data["company_name"] == "Asana"
        assert data["domain"] == "asana.com"
        assert data["segment"] == "Mid-Market"

    def test_get_company_by_domain_not_found(self, sample_companies):
        """Test getting non-existent domain"""
        response = client.get("/companies/by-domain/nonexistent.com")
        assert response.status_code == 404

        data = response.json()
        assert "not found" in data["detail"].lower()


class TestStatisticsEndpoint:
    """Tests for statistics endpoint"""

    def test_get_statistics(self, sample_companies):
        """Test getting system statistics"""
        response = client.get("/stats")
        assert response.status_code == 200

        data = response.json()

        # Overall stats
        assert data["total_companies"] == 4
        assert data["enriched_companies"] == 3
        assert data["enrichment_rate"] == "75.0%"

        # Average score (only enriched companies)
        expected_avg = (95 + 80 + 40) / 3
        assert data["average_icp_score"] == round(expected_avg, 2)

        # By segment
        assert data["by_segment"]["Enterprise"] == 1
        assert data["by_segment"]["Mid-Market"] == 1
        assert data["by_segment"]["SMB"] == 1

        # By country
        assert data["by_country"]["USA"] == 3
        assert data["by_country"]["Canada"] == 1

        # Top companies
        assert len(data["top_companies"]) == 3
        assert data["top_companies"][0]["company_name"] == "HubSpot"
        assert data["top_companies"][0]["icp_fit_score"] == 95


class TestErrorHandling:
    """Tests for error handling"""

    def test_invalid_pagination_parameters(self, sample_companies):
        """Test invalid pagination parameters"""
        response = client.get("/companies?skip=-1")
        assert response.status_code == 422  # Validation error

    def test_invalid_score_range(self, sample_companies):
        """Test invalid score range"""
        response = client.get("/companies?min_score=150")
        assert response.status_code == 422  # Validation error

    def test_invalid_limit(self, sample_companies):
        """Test limit exceeding maximum"""
        response = client.get("/companies?limit=5000")
        assert response.status_code == 422  # Validation error


class TestResponseSchema:
    """Tests for response schema validation"""

    def test_company_enriched_schema(self, sample_companies):
        """Test CompanyEnriched schema in response"""
        response = client.get("/companies/1")
        assert response.status_code == 200

        data = response.json()

        # Required fields
        assert "id" in data
        assert "company_name" in data
        assert "domain" in data
        assert "country" in data
        assert "employee_count" in data
        assert "industry_raw" in data

        # Enrichment fields
        assert "icp_fit_score" in data
        assert "segment" in data
        assert "primary_use_case" in data
        assert "risk_flags" in data
        assert "personalized_pitch" in data

        # Status fields
        assert "scraping_status" in data
        assert "enrichment_status" in data

        # Timestamps
        assert "created_at" in data

    def test_company_list_response_schema(self, sample_companies):
        """Test CompanyListResponse schema"""
        response = client.get("/companies")
        assert response.status_code == 200

        data = response.json()

        # Required fields
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "companies" in data

        # Companies is array
        assert isinstance(data["companies"], list)


# Integration test
def test_full_api_workflow(sample_companies):
    """Test complete API workflow"""

    # 1. Check health
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database_connected"] is True

    # 2. List all companies
    response = client.get("/companies")
    assert response.status_code == 200
    assert response.json()["total"] == 4

    # 3. Filter high-scoring companies
    response = client.get("/companies?min_score=80&enriched_only=true")
    assert response.status_code == 200
    companies = response.json()["companies"]
    assert len(companies) == 2
    assert all(c["icp_fit_score"] >= 80 for c in companies)

    # 4. Get specific company
    response = client.get("/companies/1")
    assert response.status_code == 200
    assert response.json()["company_name"] == "HubSpot"

    # 5. Get statistics
    response = client.get("/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_companies"] == 4
    assert stats["enriched_companies"] == 3
