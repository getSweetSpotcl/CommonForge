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
