"""
End-to-end tests for the complete pipeline.
"""

import pytest
import asyncio
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.pipeline import Pipeline
from src.db import Base
from src.models import Company

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def setup_test_db():
    """Create tables before test and drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_session(monkeypatch, setup_test_db):
    """Mock database session for testing"""
    from src import pipeline

    # Mock SessionLocal
    monkeypatch.setattr(pipeline, 'SessionLocal', TestingSessionLocal)

    # Mock check_connection to return True
    monkeypatch.setattr(pipeline, 'check_connection', lambda: True)

    # Mock init_db to do nothing (already created tables)
    monkeypatch.setattr(pipeline, 'init_db', lambda: None)

    return TestingSessionLocal


class TestPipelineIntegration:
    """Integration tests for pipeline"""

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test pipeline initialization"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_scraping=True,
            skip_enrichment=True
        )

        assert pipeline.csv_path == csv_path
        assert pipeline.dry_run is True
        assert pipeline.skip_scraping is True
        assert pipeline.skip_enrichment is True

    @pytest.mark.asyncio
    async def test_pipeline_csv_loading(self):
        """Test CSV loading step"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_scraping=True,
            skip_enrichment=True
        )

        # Load CSV
        success = pipeline._load_csv()

        assert success is True
        assert len(pipeline.structured_data) > 0
        assert pipeline.stats['csv_loaded'] > 0

        # Check data structure
        first_company = pipeline.structured_data[0]
        assert 'company_name' in first_company
        assert 'domain' in first_company
        assert 'country' in first_company
        assert 'employee_count' in first_company

    @pytest.mark.asyncio
    async def test_pipeline_csv_loading_with_limit(self):
        """Test CSV loading with max_companies limit"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            max_companies=2
        )

        success = pipeline._load_csv()

        assert success is True
        assert len(pipeline.structured_data) == 2
        assert pipeline.stats['csv_loaded'] == 2

    @pytest.mark.asyncio
    async def test_pipeline_csv_loading_file_not_found(self):
        """Test CSV loading with non-existent file"""
        csv_path = Path("data/nonexistent.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True
        )

        success = pipeline._load_csv()

        assert success is False
        assert 'CSV loading' in pipeline.stats['errors'][0]

    @pytest.mark.asyncio
    async def test_pipeline_scraping_step(self):
        """Test website scraping step"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_enrichment=True,
            max_companies=2  # Limit for faster testing
        )

        # Load CSV first
        pipeline._load_csv()

        # Scrape websites
        success = await pipeline._scrape_websites()

        assert success is True
        assert len(pipeline.scraped_data) == 2
        assert pipeline.stats['websites_scraped'] == 2

        # Check scraping results
        for result in pipeline.scraped_data:
            assert 'domain' in result
            assert 'status' in result
            assert result['status'] in ['success', 'failed']

    @pytest.mark.asyncio
    async def test_pipeline_merge_step(self):
        """Test data merging step"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_enrichment=True,
            max_companies=2
        )

        # Load and scrape
        pipeline._load_csv()
        await pipeline._scrape_websites()

        # Merge
        success = pipeline._merge_data()

        assert success is True
        assert len(pipeline.merged_data) == 2

        # Check merged data structure
        for company in pipeline.merged_data:
            assert 'company_name' in company
            assert 'domain' in company
            assert 'scraping_status' in company
            assert 'enrichment_status' in company

    @pytest.mark.asyncio
    async def test_pipeline_persistence(self, mock_session):
        """Test database persistence"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=False,  # Enable persistence
            skip_scraping=True,
            skip_enrichment=True,
            max_companies=2
        )

        # Load and merge
        pipeline._load_csv()
        pipeline.scraped_data = []
        pipeline._merge_data()

        # Persist
        success = pipeline._persist_to_db()

        assert success is True
        assert pipeline.stats['companies_persisted'] == 2

        # Verify in database
        db = TestingSessionLocal()
        companies = db.query(Company).all()
        assert len(companies) == 2
        db.close()

    @pytest.mark.asyncio
    async def test_pipeline_persistence_update(self, mock_session):
        """Test database persistence with updates"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=False,
            skip_scraping=True,
            skip_enrichment=True,
            max_companies=1
        )

        # First run - create
        pipeline._load_csv()
        pipeline.scraped_data = []
        pipeline._merge_data()
        pipeline._persist_to_db()

        # Verify created
        db = TestingSessionLocal()
        company = db.query(Company).first()
        original_name = company.company_name
        db.close()

        # Second run - update
        pipeline2 = Pipeline(
            csv_path=csv_path,
            dry_run=False,
            skip_scraping=True,
            skip_enrichment=True,
            max_companies=1
        )

        pipeline2._load_csv()
        pipeline2.scraped_data = []
        pipeline2._merge_data()
        # Modify data
        pipeline2.merged_data[0]['industry_raw'] = 'Updated Industry'
        pipeline2._persist_to_db()

        # Verify updated (not duplicated)
        db = TestingSessionLocal()
        companies = db.query(Company).all()
        assert len(companies) == 1  # Still only 1 company
        assert companies[0].company_name == original_name
        assert companies[0].industry_raw == 'Updated Industry'
        db.close()

    @pytest.mark.asyncio
    async def test_pipeline_dry_run(self):
        """Test pipeline in dry-run mode"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_scraping=True,
            skip_enrichment=True,
            max_companies=2
        )

        success = await pipeline.run()

        assert success is True
        assert pipeline.stats['csv_loaded'] == 2
        assert pipeline.stats['companies_persisted'] == 0  # No persistence in dry-run

    @pytest.mark.asyncio
    async def test_pipeline_statistics(self):
        """Test pipeline statistics tracking"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_enrichment=True,
            max_companies=2
        )

        await pipeline.run()

        # Check stats
        assert pipeline.stats['csv_loaded'] == 2
        assert pipeline.stats['websites_scraped'] == 2
        assert 'scraping_successful' in pipeline.stats
        assert isinstance(pipeline.stats['errors'], list)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip by default (requires OpenAI API key)
        reason="Requires OpenAI API key and makes real API calls"
    )
    async def test_pipeline_full_run(self, mock_session):
        """Test complete pipeline run with all steps (manual test)"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=False,
            max_companies=2  # Limit for API costs
        )

        success = await pipeline.run()

        assert success is True
        assert pipeline.stats['csv_loaded'] == 2
        assert pipeline.stats['websites_scraped'] == 2
        assert pipeline.stats['companies_enriched'] > 0
        assert pipeline.stats['companies_persisted'] == 2

        # Verify in database
        db = TestingSessionLocal()
        companies = db.query(Company).all()
        assert len(companies) == 2

        # Check enriched data
        enriched = [c for c in companies if c.enrichment_status == 'success']
        if enriched:
            assert enriched[0].icp_fit_score is not None
            assert enriched[0].segment is not None

        db.close()


class TestPipelineErrorHandling:
    """Tests for pipeline error handling"""

    @pytest.mark.asyncio
    async def test_pipeline_handles_csv_errors(self):
        """Test pipeline handles CSV errors gracefully"""
        csv_path = Path("nonexistent.csv")

        pipeline = Pipeline(csv_path=csv_path, dry_run=True)

        success = await pipeline.run()

        assert success is False
        assert len(pipeline.stats['errors']) > 0

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_scraping_errors(self):
        """Test pipeline continues even if scraping fails"""
        csv_path = Path("data/companies.csv")

        pipeline = Pipeline(
            csv_path=csv_path,
            dry_run=True,
            skip_enrichment=True,
            max_companies=1
        )

        # Mock scraping to fail
        async def mock_scrape_fail():
            raise Exception("Scraping failed")

        original_scrape = pipeline._scrape_websites
        pipeline._scrape_websites = mock_scrape_fail

        # Should still complete other steps
        success = await pipeline.run()

        # Pipeline should continue despite scraping failure
        assert pipeline.stats['csv_loaded'] > 0


# Test CLI argument parsing
def test_pipeline_cli_help():
    """Test CLI help message (doesn't run pipeline)"""
    import subprocess

    result = subprocess.run(
        ["python", "-m", "src.pipeline", "--help"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "CommonForge Pipeline" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--skip-scraping" in result.stdout
    assert "--skip-enrichment" in result.stdout
