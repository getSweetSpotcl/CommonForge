# Master Implementation Plan: AI-Powered B2B Lead Scoring System

**Project Name:** CommonForge
**Type:** AI-Powered B2B Lead Scoring Prototype
**Technology Stack:** Python 3.11+, FastAPI, LangChain, PostgreSQL, OpenAI

---

## Executive Summary

This is a comprehensive implementation plan for building an AI-powered B2B lead scoring system that:
- Ingests structured company data from CSV
- Scrapes and extracts unstructured data from company websites
- Uses LLM (via LangChain) to enrich and score companies
- Persists enriched data in PostgreSQL
- Exposes results through a FastAPI REST API

---

## Project Timeline & Phases

### Phase 1: Project Setup & Configuration (Day 1)
**Duration:** 2-3 hours
**Goal:** Establish project foundation, dependencies, and environment

**Deliverables:**
- Project structure creation
- Virtual environment and dependencies
- Environment configuration (.env template)
- Git initialization
- Basic documentation (README.md, CLAUDE.md)

---

### Phase 2: Data Layer & Models (Day 1)
**Duration:** 2-3 hours
**Goal:** Design and implement database schema and ORM models

**Deliverables:**
- SQLAlchemy database connection and session management
- Company ORM model with all required fields
- Pydantic schemas for API responses
- Database initialization script
- Migration strategy documentation

---

### Phase 3: Data Ingestion Layer (Day 1-2)
**Duration:** 3-4 hours
**Goal:** Build structured and unstructured data ingestion pipelines

**Deliverables:**
- CSV reader with data validation
- Async website scraper using HTTPX
- HTML parser with BeautifulSoup4
- Text extraction and truncation utilities
- Error handling and retry logic
- Domain normalization utilities

---

### Phase 4: LLM Processing & Enrichment (Day 2)
**Duration:** 4-5 hours
**Goal:** Implement LLM-powered enrichment pipeline using LangChain

**Deliverables:**
- LangChain chain configuration
- Prompt engineering for ICP scoring
- JSON output parser and validation
- Async processing pipeline
- Rate limiting and error handling
- Data quality checks

---

### Phase 5: API Serving Layer (Day 2-3)
**Duration:** 3-4 hours
**Goal:** Build FastAPI REST API for querying enriched companies

**Deliverables:**
- FastAPI application structure
- GET /companies endpoint with filtering
- GET /companies/{id} endpoint
- Query parameter validation
- OpenAPI/Swagger documentation
- CORS and middleware configuration

---

### Phase 6: Pipeline Orchestration (Day 3)
**Duration:** 2-3 hours
**Goal:** Create end-to-end pipeline orchestration

**Deliverables:**
- Main pipeline.py orchestration script
- CLI arguments and flags
- Progress tracking and logging
- Database initialization command
- Idempotency and resumability
- Performance metrics collection

---

### Phase 7: Testing & Validation (Day 3)
**Duration:** 3-4 hours
**Goal:** Ensure system reliability and correctness

**Deliverables:**
- Unit tests for core utilities
- Integration tests for pipeline
- API endpoint tests
- Mock LLM responses for testing
- Test data fixtures
- CI/CD test configuration

---

### Phase 8: Documentation & Polish (Day 3-4)
**Duration:** 2-3 hours
**Goal:** Complete documentation and prepare for demonstration

**Deliverables:**
- Comprehensive README.md
- API usage examples
- Setup and deployment guide
- Architecture diagrams
- Video walkthrough script
- Code cleanup and formatting

---

## Success Criteria

### Technical Requirements
- ✅ All CSV companies successfully ingested
- ✅ Website scraping with 90%+ success rate
- ✅ LLM enrichment produces valid JSON for all companies
- ✅ All data persisted correctly in PostgreSQL
- ✅ API returns correct filtered results
- ✅ OpenAPI documentation fully functional

### Quality Requirements
- ✅ Clean, modular, well-documented code
- ✅ Proper error handling and logging
- ✅ Async operations where appropriate
- ✅ Type hints throughout codebase
- ✅ No hardcoded credentials
- ✅ Separation of concerns maintained

### Performance Requirements
- ✅ Pipeline processes 5 companies in < 2 minutes
- ✅ API response time < 100ms for queries
- ✅ Proper async/await for I/O operations
- ✅ Database queries optimized with indexes

---

## Technical Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
│  ┌──────────────────┐       ┌──────────────────┐           │
│  │  companies.csv   │       │  Company Websites │           │
│  │  (Structured)    │       │  (Unstructured)   │           │
│  └────────┬─────────┘       └────────┬──────────┘           │
└───────────┼──────────────────────────┼──────────────────────┘
            │                          │
            ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  INGESTION LAYER                             │
│  ┌──────────────────┐       ┌──────────────────┐           │
│  │ Pandas CSV       │       │ HTTPX + BS4      │           │
│  │ Reader           │       │ Web Scraper      │           │
│  └────────┬─────────┘       └────────┬──────────┘           │
└───────────┼──────────────────────────┼──────────────────────┘
            │                          │
            └──────────┬───────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 PROCESSING LAYER                             │
│  ┌──────────────────────────────────────────────┐           │
│  │  LangChain LLM Enrichment Chain              │           │
│  │  - Prompt Engineering                        │           │
│  │  - OpenAI GPT-4 API                          │           │
│  │  - JSON Output Parsing                       │           │
│  │  - Async Processing                          │           │
│  └────────────────────┬─────────────────────────┘           │
└─────────────────────────┼───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  PERSISTENCE LAYER                           │
│  ┌──────────────────────────────────────────────┐           │
│  │  PostgreSQL Database                         │           │
│  │  - SQLAlchemy ORM                            │           │
│  │  - Company Model                             │           │
│  │  - Indexes on score, segment, country        │           │
│  └────────────────────┬─────────────────────────┘           │
└─────────────────────────┼───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVING LAYER                             │
│  ┌──────────────────────────────────────────────┐           │
│  │  FastAPI REST API                            │           │
│  │  - GET /companies (with filters)             │           │
│  │  - GET /companies/{id}                       │           │
│  │  - Pydantic validation                       │           │
│  │  - OpenAPI/Swagger docs                      │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
CommonForge/
├── README.md                    # Project overview and setup guide
├── CLAUDE.md                    # AI assistant context file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
│
├── data/
│   └── companies.csv            # Sample company data
│
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── db.py                    # Database connection and session
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic schemas for API
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── structured.py        # CSV loading and validation
│   │   └── unstructured.py      # Website scraping and parsing
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── cleaning.py          # Data cleaning and joining
│   │   └── llm_chain.py         # LangChain enrichment pipeline
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI application
│   │
│   └── pipeline.py              # Main orchestration script
│
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py
│   ├── test_processing.py
│   └── test_api.py
│
├── scripts/
│   ├── init_db.sh               # Database initialization
│   └── run_pipeline.sh          # Pipeline execution helper
│
└── plan/                        # Implementation plans (this folder)
    ├── 00-master-plan.md
    ├── 01-architecture.md
    ├── 02-phase1-setup.md
    ├── 03-phase2-data-layer.md
    ├── 04-phase3-ingestion.md
    ├── 05-phase4-processing.md
    ├── 06-phase5-api.md
    ├── 07-phase6-orchestration.md
    └── 08-phase7-testing.md
```

---

## Key Design Decisions

### 1. Async vs Sync
- **Website scraping:** Async (HTTPX) - multiple sites in parallel
- **LLM calls:** Async - can process multiple companies concurrently
- **Database operations:** Sync - simpler for this prototype
- **API endpoints:** Async - FastAPI best practices

### 2. Data Processing Strategy
- **Batch processing:** Process all companies in one pipeline run
- **Idempotency:** Support re-running pipeline without duplicates
- **Error resilience:** Continue processing on individual failures
- **Checkpointing:** Track progress for resumability

### 3. LLM Strategy
- **Model:** OpenAI GPT-4.1-mini (cost-effective, fast)
- **Prompt design:** Structured prompt with clear JSON schema
- **Output parsing:** JsonOutputParser for reliable extraction
- **Rate limiting:** Implement backoff and retry logic
- **Cost optimization:** Cache results, batch where possible

### 4. API Design
- **RESTful:** Standard HTTP methods and status codes
- **Filtering:** Query parameters for min_score, country, segment
- **Pagination:** Prepare for future implementation
- **Validation:** Pydantic for request/response validation
- **Documentation:** Auto-generated OpenAPI/Swagger

### 5. Testing Strategy
- **Unit tests:** Core utilities and parsers
- **Integration tests:** End-to-end pipeline
- **Mocking:** Mock LLM calls for deterministic tests
- **Fixtures:** Sample data for consistent testing
- **Coverage:** Aim for 80%+ code coverage

---

## Risk Assessment & Mitigation

### Risk 1: Website Scraping Failures
**Likelihood:** High
**Impact:** Medium
**Mitigation:**
- Implement robust error handling
- Add retry logic with exponential backoff
- Gracefully handle missing or malformed HTML
- Log failures for manual review

### Risk 2: LLM API Rate Limits
**Likelihood:** Medium
**Impact:** High
**Mitigation:**
- Implement rate limiting
- Add retry logic with backoff
- Consider using lower-tier models for testing
- Monitor API usage and costs

### Risk 3: Inconsistent LLM Outputs
**Likelihood:** Medium
**Impact:** Medium
**Mitigation:**
- Use structured output parsing (JsonOutputParser)
- Validate outputs against Pydantic schemas
- Log and handle parsing errors gracefully
- Implement fallback scoring logic

### Risk 4: Database Connection Issues
**Likelihood:** Low
**Impact:** High
**Mitigation:**
- Use connection pooling
- Implement retry logic for transactions
- Validate database connection on startup
- Provide clear error messages for setup issues

---

## Next Steps

1. **Begin Phase 1:** Set up project structure and dependencies
2. **Review architecture:** Ensure alignment with requirements
3. **Validate approach:** Confirm technical decisions with stakeholders
4. **Start implementation:** Follow phase-by-phase plan

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
