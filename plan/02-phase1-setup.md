# Phase 1: Project Setup & Configuration

**Duration:** 2-3 hours
**Priority:** Critical - Foundation for all other phases
**Dependencies:** None

---

## Objectives

1. Create complete project structure
2. Set up Python virtual environment
3. Install all dependencies
4. Configure environment variables
5. Initialize Git repository
6. Create foundational documentation

---

## Task Checklist

### 1.1 Create Project Directory Structure

```bash
# Create all directories
mkdir -p src/{ingestion,processing,api}
mkdir -p tests
mkdir -p scripts
mkdir -p data
mkdir -p plan

# Create __init__.py files for Python packages
touch src/__init__.py
touch src/ingestion/__init__.py
touch src/processing/__init__.py
touch src/api/__init__.py
touch tests/__init__.py
```

**Expected Structure:**
```
CommonForge/
├── src/
│   ├── __init__.py
│   ├── config.py               # To be created
│   ├── db.py                   # To be created
│   ├── models.py               # To be created
│   ├── schemas.py              # To be created
│   ├── pipeline.py             # To be created
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── structured.py       # To be created
│   │   └── unstructured.py     # To be created
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── cleaning.py         # To be created
│   │   └── llm_chain.py        # To be created
│   └── api/
│       ├── __init__.py
│       └── main.py             # To be created
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py       # To be created
│   ├── test_processing.py      # To be created
│   └── test_api.py             # To be created
├── scripts/
│   ├── init_db.sh              # To be created
│   └── run_pipeline.sh         # To be created
├── data/
│   └── companies.csv           # To be created
├── docs/
│   └── req.md                  # Already exists
├── plan/                       # Already exists
│   ├── 00-master-plan.md
│   ├── 01-architecture.md
│   └── ...
├── README.md                   # To be created
├── CLAUDE.md                   # To be created
├── requirements.txt            # To be created
├── .env.example                # To be created
├── .gitignore                  # To be created
└── pytest.ini                  # To be created
```

---

### 1.2 Set Up Python Virtual Environment

```bash
# Create virtual environment with Python 3.11+
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Upgrade pip
pip install --upgrade pip
```

**Verification:**
```bash
python --version  # Should show Python 3.11+
which python      # Should point to venv/bin/python
```

---

### 1.3 Create requirements.txt

**Content:**
```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0

# Data Validation
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9

# Data Processing
pandas==2.1.4

# HTTP & Web Scraping
httpx==0.26.0
beautifulsoup4==4.12.3
lxml==5.1.0

# LLM & AI
langchain==0.1.0
langchain-openai==0.0.2
openai==1.6.1

# Configuration
python-dotenv==1.0.0

# Testing
pytest==7.4.4
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx-mock==0.7.0

# Development
black==23.12.1
flake8==7.0.0
mypy==1.8.0
```

**Installation:**
```bash
pip install -r requirements.txt
```

**Verification:**
```bash
pip list | grep fastapi
pip list | grep langchain
pip list | grep sqlalchemy
```

---

### 1.4 Create .env.example Template

**File:** `.env.example`

```bash
# Database Configuration
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/commonforge

# OpenAI API Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1000

# Web Scraping Configuration
SCRAPER_TIMEOUT=10
SCRAPER_MAX_RETRIES=3
SCRAPER_USER_AGENT=CommonForge Lead Scorer/1.0

# Processing Configuration
MAX_WEBSITE_TEXT_LENGTH=3000
CONCURRENT_LLM_CALLS=3

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Logging
LOG_LEVEL=INFO
```

**Action Items:**
1. Copy `.env.example` to `.env`
2. Fill in actual credentials (DO NOT COMMIT `.env`)
3. Ensure `.env` is in `.gitignore`

```bash
cp .env.example .env
# Edit .env with actual credentials
```

---

### 1.5 Create .gitignore

**File:** `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# Environment Variables
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# Jupyter Notebooks
.ipynb_checkpoints

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp
```

---

### 1.6 Create pytest.ini

**File:** `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

---

### 1.7 Create Sample Data File

**File:** `data/companies.csv`

```csv
company_name,domain,country,employee_count,industry_raw
HubSpot,hubspot.com,USA,7400,Marketing & CRM Software
Asana,asana.com,USA,1900,Work Management Software
Monday.com,monday.com,Israel,1800,Work OS / Collaboration
Notion,notion.so,USA,600,Knowledge Management / Productivity
Intercom,intercom.com,USA,1300,Customer Messaging Platform
```

**Verification:**
```bash
cat data/companies.csv
wc -l data/companies.csv  # Should show 6 (header + 5 companies)
```

---

### 1.8 Initialize Git Repository

```bash
# Initialize repository
git init

# Add all files (respecting .gitignore)
git add .

# Initial commit
git commit -m "Initial project setup

- Created project structure
- Added requirements.txt with all dependencies
- Set up environment configuration
- Added sample company data
- Configured pytest for testing"
```

**Verification:**
```bash
git status
git log --oneline
```

---

### 1.9 Create README.md

**File:** `README.md`

```markdown
# CommonForge: AI-Powered B2B Lead Scoring

An AI-powered lead scoring system that combines structured company data with unstructured web content to generate intelligent ICP (Ideal Customer Profile) fit scores and personalized sales insights.

## Features

- **Multi-Source Data Ingestion:** CSV + web scraping
- **AI-Powered Enrichment:** LLM-based analysis using LangChain
- **Intelligent Scoring:** 0-100 ICP fit score for each company
- **Segment Classification:** Automatic SMB/Mid-Market/Enterprise categorization
- **Personalized Insights:** Custom sales pitches and risk flags
- **REST API:** FastAPI-powered API with filtering and search

## Tech Stack

- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **LLM Framework:** LangChain
- **LLM Provider:** OpenAI GPT-4
- **HTTP Client:** HTTPX (async)
- **HTML Parsing:** BeautifulSoup4
- **Data Processing:** Pandas

## Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (local or remote)
- OpenAI API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd CommonForge
   ```

2. **Create virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database:**
   ```bash
   # Create PostgreSQL database
   createdb commonforge

   # Initialize tables
   python -m src.pipeline --init-db
   ```

### Usage

**Run the enrichment pipeline:**
```bash
python -m src.pipeline
```

**Start the API server:**
```bash
uvicorn src.api.main:app --reload
```

**Access the API:**
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

### API Endpoints

**List companies with filters:**
```bash
GET /companies?min_score=70&segment=Mid-Market
```

**Get specific company:**
```bash
GET /companies/{company_id}
```

## Development

**Run tests:**
```bash
pytest
```

**Run tests with coverage:**
```bash
pytest --cov=src --cov-report=html
```

**Code formatting:**
```bash
black src/ tests/
```

**Linting:**
```bash
flake8 src/ tests/
mypy src/
```

## Project Structure

```
CommonForge/
├── src/              # Source code
│   ├── api/         # FastAPI application
│   ├── ingestion/   # Data ingestion (CSV + web scraping)
│   ├── processing/  # LLM enrichment pipeline
│   ├── config.py    # Configuration management
│   ├── db.py        # Database connection
│   ├── models.py    # SQLAlchemy models
│   ├── schemas.py   # Pydantic schemas
│   └── pipeline.py  # Main orchestration
├── tests/           # Test suite
├── data/            # Sample data
├── plan/            # Implementation plans
└── scripts/         # Helper scripts
```

## Architecture

See [plan/01-architecture.md](plan/01-architecture.md) for detailed technical architecture.

## License

MIT License - for evaluation and demonstration purposes.

## Author

Gustavo Cortínez - Principal AI Engineer Candidate
```

---

### 1.10 Create CLAUDE.md

**File:** `CLAUDE.md`

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CommonForge is an AI-powered B2B lead scoring system built with Python, FastAPI, LangChain, and PostgreSQL. It ingests company data from CSV and websites, enriches it using LLM, and exposes results via REST API.

## Development Commands

### Setup
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with credentials
```

### Database
```bash
# Initialize database tables
python -m src.pipeline --init-db

# Reset database (development only)
python -m src.pipeline --reset-db
```

### Running the Pipeline
```bash
# Run full enrichment pipeline
python -m src.pipeline

# Run with specific CSV
python -m src.pipeline --csv-path data/companies.csv

# Dry run (no database writes)
python -m src.pipeline --dry-run
```

### Running the API
```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ingestion.py

# Run specific test
pytest tests/test_ingestion.py::test_load_csv
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Architecture

### Project Structure
- `src/config.py` - Environment configuration using Pydantic Settings
- `src/db.py` - SQLAlchemy database connection and session management
- `src/models.py` - ORM models (Company table)
- `src/schemas.py` - Pydantic models for API validation
- `src/ingestion/` - Data ingestion layer (CSV + web scraping)
- `src/processing/` - LLM enrichment pipeline (LangChain)
- `src/api/` - FastAPI REST API
- `src/pipeline.py` - Main orchestration script

### Key Technologies
- **FastAPI:** Async web framework for API
- **SQLAlchemy:** ORM for PostgreSQL
- **LangChain:** LLM orchestration framework
- **HTTPX:** Async HTTP client for web scraping
- **BeautifulSoup4:** HTML parsing
- **Pydantic:** Data validation and settings

### Database Schema
The main model is `Company` with fields:
- Structured data: company_name, domain, country, employee_count, industry_raw
- Unstructured data: website_text_snippet, scraping_status
- Enriched data: icp_fit_score, segment, primary_use_case, risk_flags, personalized_pitch

### Data Flow
1. Load CSV with pandas
2. Scrape websites asynchronously with HTTPX
3. Extract text with BeautifulSoup4
4. Merge structured + unstructured data
5. Enrich with LLM via LangChain
6. Persist to PostgreSQL
7. Serve via FastAPI

## Common Tasks

### Adding a new company field
1. Update `Company` model in `src/models.py`
2. Create migration or add to `create_all()`
3. Update `CompanyEnriched` schema in `src/schemas.py`
4. Update LLM prompt if field is AI-generated

### Modifying LLM enrichment
1. Edit prompt template in `src/processing/llm_chain.py`
2. Update `CompanyEnrichment` Pydantic model if schema changes
3. Test with sample data before full run

### Adding new API endpoint
1. Add route in `src/api/main.py`
2. Create request/response schemas in `src/schemas.py`
3. Add tests in `tests/test_api.py`

## Troubleshooting

### Database connection errors
- Check `DATABASE_URL` in `.env`
- Verify PostgreSQL is running
- Ensure database exists: `createdb commonforge`

### LLM API errors
- Check `OPENAI_API_KEY` in `.env`
- Verify API key is valid
- Check OpenAI rate limits

### Scraping failures
- Check internet connectivity
- Verify domains are accessible
- Review `SCRAPER_TIMEOUT` setting

## Important Notes

- All code should use async/await for I/O operations
- Type hints are required for all functions
- Use Pydantic for data validation
- Log errors and important events
- Never commit `.env` file
- Keep LLM prompts modular and testable
```

---

## Verification Steps

After completing Phase 1, verify:

1. **Directory Structure:**
   ```bash
   tree -L 2 -I 'venv|__pycache__|*.pyc'
   ```

2. **Python Environment:**
   ```bash
   python --version  # 3.11+
   pip list | wc -l  # Should show ~30+ packages
   ```

3. **Git Repository:**
   ```bash
   git status        # Should be clean
   git log --oneline # Should show initial commit
   ```

4. **Environment Configuration:**
   ```bash
   test -f .env && echo "✓ .env exists"
   test -f .env.example && echo "✓ .env.example exists"
   ```

5. **Sample Data:**
   ```bash
   wc -l data/companies.csv  # Should be 6 lines
   ```

6. **Documentation:**
   ```bash
   test -f README.md && echo "✓ README.md exists"
   test -f CLAUDE.md && echo "✓ CLAUDE.md exists"
   ```

---

## Next Steps

Once Phase 1 is complete:
1. Review all created files
2. Ensure `.env` has real credentials (not committed)
3. Proceed to **Phase 2: Data Layer & Models**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Create directory structure | 10 min |
| Set up virtual environment | 10 min |
| Create requirements.txt | 10 min |
| Install dependencies | 15 min |
| Create configuration files | 20 min |
| Create sample data | 10 min |
| Initialize Git | 10 min |
| Write README.md | 30 min |
| Write CLAUDE.md | 30 min |
| Verification | 15 min |
| **Total** | **2.5 hours** |
```

