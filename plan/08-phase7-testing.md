# Phase 7: Testing & Quality Assurance

**Duration:** 3-4 hours
**Priority:** Critical - Ensures system reliability
**Dependencies:** All previous phases

---

## Objectives

1. Create comprehensive test suite
2. Achieve >80% code coverage
3. Add integration tests
4. Create test fixtures and mocks
5. Set up CI/CD testing pipeline
6. Perform manual QA testing
7. Document testing procedures

---

## Test Strategy

### Testing Pyramid

```
        /\
       /  \      E2E Tests (Few)
      /____\     - Full pipeline test
     /      \    - API integration tests
    /________\
   /          \  Integration Tests (Some)
  /____________\ - Component integration
 /              \
/________________\ Unit Tests (Many)
                   - Individual functions
                   - Data transformations
                   - Utilities
```

---

## Task Checklist

### 7.1 Complete Unit Test Suite

**File:** `tests/test_unit.py`

```python
"""
Comprehensive unit tests for individual components.
"""

import pytest
from src.ingestion.structured import CSVIngestor
from src.processing.cleaning import merge_structured_unstructured


class TestDomainNormalization:
    """Tests for domain normalization"""

    @pytest.mark.parametrize("input_domain,expected", [
        ("HTTP://WWW.EXAMPLE.COM", "example.com"),
        ("https://example.com/", "example.com"),
        ("www.example.com", "example.com"),
        ("example.com:8080", "example.com"),
        ("example.com/path/to/page", "example.com"),
        ("EXAMPLE.COM", "example.com"),
        ("  example.com  ", "example.com"),
    ])
    def test_normalize_domain(self, input_domain, expected):
        """Test various domain normalization cases"""
        result = CSVIngestor._normalize_domain(input_domain)
        assert result == expected


class TestDataCleaning:
    """Tests for data cleaning utilities"""

    def test_merge_preserves_all_fields(self):
        """Test that merge preserves all data fields"""
        structured = [{
            'company_name': 'Test',
            'domain': 'test.com',
            'country': 'USA',
            'employee_count': 100,
            'industry_raw': 'Tech'
        }]

        scraped = [{
            'domain': 'test.com',
            'text_snippet': 'Sample text',
            'status': 'success',
            'error': None
        }]

        merged = merge_structured_unstructured(structured, scraped)

        assert len(merged) == 1
        assert merged[0]['company_name'] == 'Test'
        assert merged[0]['website_text_snippet'] == 'Sample text'
        assert merged[0]['scraping_status'] == 'success'

    def test_merge_handles_missing_scrape_data(self):
        """Test merge when scraping data is missing"""
        structured = [{
            'company_name': 'Test',
            'domain': 'test.com',
            'country': 'USA',
            'employee_count': 100,
            'industry_raw': 'Tech'
        }]

        scraped = []  # Empty scraping results

        merged = merge_structured_unstructured(structured, scraped)

        assert len(merged) == 1
        assert merged[0]['website_text_snippet'] is None
        assert merged[0]['scraping_status'] == 'failed'
```

---

### 7.2 Integration Tests

**File:** `tests/test_integration.py`

```python
"""
Integration tests for component interactions.
"""

import pytest
import asyncio
from pathlib import Path
from src.ingestion.structured import load_companies_from_csv
from src.ingestion.unstructured import scrape_companies
from src.processing.cleaning import merge_structured_unstructured


@pytest.mark.integration
class TestIngestionIntegration:
    """Integration tests for data ingestion"""

    def test_csv_to_dict_pipeline(self):
        """Test complete CSV loading pipeline"""
        csv_path = Path("data/companies.csv")
        companies = load_companies_from_csv(csv_path)

        assert isinstance(companies, list)
        assert len(companies) > 0
        assert all(isinstance(c, dict) for c in companies)
        assert all('domain' in c for c in companies)
        assert all('company_name' in c for c in companies)

    @pytest.mark.asyncio
    async def test_scraping_integration(self):
        """Test scraping multiple domains"""
        domains = ['example.com', 'python.org']
        results = await scrape_companies(domains)

        assert len(results) == len(domains)
        assert all('domain' in r for r in results)
        assert all('status' in r for r in results)
        assert all(r['status'] in ['success', 'failed'] for r in results)


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations"""

    def test_create_and_query_company(self, db_session):
        """Test creating and querying companies"""
        from src.models import Company

        # Create company
        company = Company(
            company_name="Integration Test Corp",
            domain="integration-test.com",
            country="USA",
            employee_count=50,
            industry_raw="Testing",
            scraping_status="pending",
            enrichment_status="pending",
        )

        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

        # Query back
        queried = db_session.query(Company).filter_by(
            domain="integration-test.com"
        ).first()

        assert queried is not None
        assert queried.company_name == "Integration Test Corp"
        assert queried.id == company.id
```

---

### 7.3 Mock LLM for Testing

**File:** `tests/conftest.py`

```python
"""
Pytest configuration and fixtures.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db import Base


# Test database fixture
@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///./test.db")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Create database session for testing"""
    SessionLocal = sessionmaker(bind=test_db)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# Mock LLM responses
@pytest.fixture
def mock_llm_response():
    """Mock LLM enrichment response"""
    return {
        'icp_fit_score': 85,
        'segment': 'Mid-Market',
        'primary_use_case': 'AI-powered workflow automation',
        'risk_flags': ['Limited budget', 'Small team'],
        'personalized_pitch': 'Your company could benefit from our AI automation platform.',
    }


@pytest.fixture
def sample_company_data():
    """Sample company data for testing"""
    return {
        'company_name': 'Test Corp',
        'domain': 'test.com',
        'country': 'USA',
        'employee_count': 100,
        'industry_raw': 'Technology',
        'website_text_snippet': 'We are a technology company...',
        'scraping_status': 'success',
        'scraping_error': None,
    }
```

---

### 7.4 Test Coverage Configuration

**File:** `.coveragerc`

```ini
[run]
source = src
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod

[html]
directory = htmlcov
```

---

### 7.5 CI/CD Test Configuration

**File:** `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: commonforge_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run unit tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/commonforge_test
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        pytest tests/test_unit.py -v --cov=src --cov-report=xml

    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/commonforge_test
      run: |
        pytest tests/test_integration.py -v -m integration

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

---

### 7.6 Manual QA Test Plan

**File:** `tests/manual_qa_checklist.md`

```markdown
# Manual QA Testing Checklist

## Pre-Testing Setup
- [ ] PostgreSQL running and accessible
- [ ] `.env` file configured with valid credentials
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] Database initialized (`python -m src.pipeline --init-db`)

## Data Ingestion Tests

### CSV Loading
- [ ] Load sample CSV successfully
- [ ] Handle missing columns gracefully
- [ ] Normalize domains correctly
- [ ] Remove duplicate domains
- [ ] Validate employee counts

### Web Scraping
- [ ] Scrape at least 3 websites successfully
- [ ] Handle timeout errors gracefully
- [ ] Retry failed requests
- [ ] Extract meaningful text content
- [ ] Truncate long content appropriately

## LLM Enrichment Tests

### Prompt Quality
- [ ] ICP scores are in valid range (0-100)
- [ ] Segments are valid (SMB/Mid-Market/Enterprise)
- [ ] Use cases are meaningful and specific
- [ ] Risk flags are relevant
- [ ] Pitches are personalized

### Consistency
- [ ] Similar companies get similar scores
- [ ] Scores align with company characteristics
- [ ] Segment matches employee count appropriately

## Database Tests

### Data Persistence
- [ ] Companies persist correctly
- [ ] All fields saved properly
- [ ] Timestamps populated
- [ ] Upsert logic works (no duplicates)

### Queries
- [ ] Can query by ID
- [ ] Can query by domain
- [ ] Filtering by score works
- [ ] Filtering by segment works
- [ ] Filtering by country works

## API Tests

### Endpoints
- [ ] GET / returns health status
- [ ] GET /health checks database
- [ ] GET /companies returns list
- [ ] GET /companies?min_score=X filters correctly
- [ ] GET /companies?segment=Y filters correctly
- [ ] GET /companies/{id} returns single company
- [ ] GET /companies/by-domain/{domain} works
- [ ] GET /stats returns correct statistics

### API Documentation
- [ ] Swagger UI accessible at /docs
- [ ] All endpoints documented
- [ ] Request/response schemas visible
- [ ] "Try it out" functionality works

### Error Handling
- [ ] 404 for non-existent company
- [ ] 400 for invalid parameters
- [ ] 500 errors logged properly

## Pipeline Tests

### End-to-End
- [ ] `--init-db` creates tables
- [ ] Full pipeline runs without errors
- [ ] `--dry-run` doesn't persist data
- [ ] Progress logging is clear
- [ ] Summary statistics are accurate

### Error Recovery
- [ ] Handles scraping failures gracefully
- [ ] Continues on individual LLM errors
- [ ] Database errors don't crash pipeline

## Performance Tests

### Scalability
- [ ] 5 companies complete in < 5 minutes
- [ ] 10 companies complete in < 10 minutes
- [ ] API responses < 100ms
- [ ] Concurrent scraping works
- [ ] Rate limiting prevents API errors

## Security Tests

### Configuration
- [ ] .env not committed to git
- [ ] No hardcoded credentials
- [ ] API keys properly loaded from environment

### SQL Injection
- [ ] User input sanitized
- [ ] ORM prevents injection
- [ ] Query parameters validated

## Documentation Tests

- [ ] README is complete and accurate
- [ ] CLAUDE.md has correct commands
- [ ] API examples work as shown
- [ ] Setup instructions are correct

## Final Acceptance

- [ ] All automated tests pass
- [ ] Code coverage > 80%
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Ready for demo
```

---

## Running Tests

### 7.7 Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Slow tests (LLM calls)

# Run tests in parallel
pytest -n auto
```

### 7.8 Generate Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open report
open htmlcov/index.html  # macOS
# or xdg-open htmlcov/index.html  # Linux
```

---

## Quality Metrics

### Target Metrics
- **Code Coverage:** >80%
- **Test Pass Rate:** 100%
- **API Response Time:** <100ms
- **Pipeline Success Rate:** >95%

### Monitoring
```bash
# Check test status
pytest --collect-only

# Run with verbose output
pytest -v

# Show slowest tests
pytest --durations=10
```

---

## Common Test Failures & Solutions

### Issue 1: Database Connection Errors in Tests

**Solution:**
```python
# Use test database in conftest.py
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
```

### Issue 2: Async Test Failures

**Solution:**
```python
# Install pytest-asyncio
pip install pytest-asyncio

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Issue 3: Flaky Network Tests

**Solution:**
```python
# Mock network calls
@pytest.fixture
def mock_httpx(monkeypatch):
    async def mock_get(*args, **kwargs):
        return MockResponse(200, "test content")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
```

---

## Success Criteria

After completing Phase 7, you should have:

- ✅ Comprehensive test suite
- ✅ >80% code coverage
- ✅ All tests passing
- ✅ CI/CD pipeline configured
- ✅ Manual QA checklist completed
- ✅ Performance metrics met
- ✅ System ready for production

---

## Next Steps

Once Phase 7 is complete:
1. Review all test results
2. Fix any failing tests
3. Improve coverage for low-coverage areas
4. **Project is ready for demonstration!**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Write unit tests | 60 min |
| Write integration tests | 45 min |
| Set up test fixtures | 30 min |
| Configure coverage | 20 min |
| Manual QA testing | 60 min |
| CI/CD configuration | 30 min |
| Documentation | 20 min |
| **Total** | **4 hours** |
