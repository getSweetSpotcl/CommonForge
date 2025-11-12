# Technical Architecture: AI-Powered B2B Lead Scoring System

**Document Version:** 1.0
**Last Updated:** 2025-11-11

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Database Schema](#database-schema)
6. [API Specification](#api-specification)
7. [Security Considerations](#security-considerations)
8. [Scalability & Performance](#scalability--performance)

---

## System Overview

### Purpose
Build an AI-powered lead scoring system that combines structured company data with unstructured web content to generate intelligent ICP (Ideal Customer Profile) fit scores and personalized sales insights.

### Core Capabilities
1. **Data Ingestion:** Multi-source data collection (CSV + web scraping)
2. **AI Enrichment:** LLM-powered analysis and scoring
3. **Data Persistence:** Reliable storage of enriched company profiles
4. **API Access:** RESTful interface for querying scored companies

### Design Principles
- **Modularity:** Clear separation between ingestion, processing, and serving
- **Async-First:** Leverage Python async for I/O-bound operations
- **Type Safety:** Comprehensive type hints and Pydantic validation
- **Observability:** Structured logging at each pipeline stage
- **Resilience:** Graceful error handling and retry logic

---

## Component Architecture

### 1. Configuration Layer (`src/config.py`)

**Purpose:** Centralized configuration management using Pydantic Settings

**Key Features:**
- Environment variable loading from `.env`
- Validation of required configuration
- Type-safe access to settings
- Separate configs for dev/staging/prod

**Schema:**
```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # LLM Provider
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 1000

    # Scraping
    SCRAPER_TIMEOUT: int = 10
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_USER_AGENT: str = "CommonForge Lead Scorer/1.0"

    # Processing
    MAX_WEBSITE_TEXT_LENGTH: int = 3000
    CONCURRENT_LLM_CALLS: int = 3

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
```

---

### 2. Database Layer (`src/db.py`, `src/models.py`)

**Purpose:** PostgreSQL connection management and ORM models

#### Connection Management (`src/db.py`)
- SQLAlchemy engine creation
- Session factory with context manager
- Connection pooling configuration
- Health check utilities

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### ORM Models (`src/models.py`)

**Company Model:**
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from src.db import Base

class Company(Base):
    __tablename__ = "companies"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Structured data (from CSV)
    company_name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    country = Column(String(100), nullable=False, index=True)
    employee_count = Column(Integer, nullable=False)
    industry_raw = Column(String(255), nullable=False)

    # Unstructured data (from scraping)
    website_text_snippet = Column(Text, nullable=True)
    scraping_status = Column(String(50), default="pending")  # pending, success, failed
    scraping_error = Column(Text, nullable=True)

    # LLM enrichment outputs
    icp_fit_score = Column(Integer, nullable=True, index=True)
    segment = Column(String(50), nullable=True, index=True)  # SMB, Mid-Market, Enterprise
    primary_use_case = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=True)  # List of strings
    personalized_pitch = Column(Text, nullable=True)
    enrichment_status = Column(String(50), default="pending")  # pending, success, failed
    enrichment_error = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.company_name}, score={self.icp_fit_score})>"
```

**Indexes:**
- `id` (primary key, automatic)
- `company_name` (for name-based searches)
- `domain` (unique, for deduplication)
- `country` (for geographic filtering)
- `icp_fit_score` (for score-based queries)
- `segment` (for segment filtering)

---

### 3. Schema Layer (`src/schemas.py`)

**Purpose:** Pydantic models for API request/response validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class CompanyBase(BaseModel):
    company_name: str
    domain: str
    country: str
    employee_count: int
    industry_raw: str

class CompanyEnriched(CompanyBase):
    id: int
    website_text_snippet: Optional[str] = None
    icp_fit_score: Optional[int] = Field(None, ge=0, le=100)
    segment: Optional[str] = None
    primary_use_case: Optional[str] = None
    risk_flags: Optional[List[str]] = None
    personalized_pitch: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CompanyListResponse(BaseModel):
    total: int
    companies: List[CompanyEnriched]

class CompanyQuery(BaseModel):
    min_score: int = Field(0, ge=0, le=100)
    country: Optional[str] = None
    segment: Optional[str] = None

    @validator('segment')
    def validate_segment(cls, v):
        if v and v not in ["SMB", "Mid-Market", "Enterprise"]:
            raise ValueError("Segment must be SMB, Mid-Market, or Enterprise")
        return v
```

---

### 4. Ingestion Layer

#### 4.1 Structured Ingestion (`src/ingestion/structured.py`)

**Purpose:** Load and validate CSV data

**Functions:**
```python
import pandas as pd
from typing import List, Dict
from pathlib import Path

def load_companies_csv(csv_path: Path) -> pd.DataFrame:
    """
    Load companies from CSV with validation

    Expected columns:
    - company_name
    - domain
    - country
    - employee_count
    - industry_raw
    """
    df = pd.read_csv(csv_path)

    # Validate required columns
    required_columns = ['company_name', 'domain', 'country', 'employee_count', 'industry_raw']
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Data cleaning
    df['domain'] = df['domain'].str.strip().str.lower()
    df['domain'] = df['domain'].str.replace('http://', '').str.replace('https://', '')
    df['domain'] = df['domain'].str.replace('www.', '')
    df['company_name'] = df['company_name'].str.strip()
    df['country'] = df['country'].str.strip()

    # Remove duplicates by domain
    df = df.drop_duplicates(subset=['domain'], keep='first')

    # Validate employee_count is numeric
    df['employee_count'] = pd.to_numeric(df['employee_count'], errors='coerce')
    df = df.dropna(subset=['employee_count'])
    df['employee_count'] = df['employee_count'].astype(int)

    return df

def dataframe_to_dicts(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to list of dictionaries"""
    return df.to_dict('records')
```

#### 4.2 Unstructured Ingestion (`src/ingestion/unstructured.py`)

**Purpose:** Scrape and extract text from company websites

**Key Components:**
- Async HTTP client (HTTPX)
- HTML parsing (BeautifulSoup4)
- Text extraction heuristics
- Error handling and retries

```python
import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Optional, Dict
from src.config import settings
import logging

logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self):
        self.timeout = settings.SCRAPER_TIMEOUT
        self.max_retries = settings.SCRAPER_MAX_RETRIES
        self.user_agent = settings.SCRAPER_USER_AGENT

    async def fetch_website(self, domain: str) -> Dict[str, any]:
        """
        Fetch and parse website content

        Returns:
            {
                'domain': str,
                'text_snippet': Optional[str],
                'status': 'success' | 'failed',
                'error': Optional[str]
            }
        """
        url = f"https://{domain}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(
                        url,
                        headers={'User-Agent': self.user_agent},
                        follow_redirects=True
                    )
                    response.raise_for_status()

                    # Parse HTML
                    text_snippet = self._extract_text(response.text)

                    return {
                        'domain': domain,
                        'text_snippet': text_snippet,
                        'status': 'success',
                        'error': None
                    }

                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for {domain}: {e}")
                    if attempt == self.max_retries - 1:
                        return {
                            'domain': domain,
                            'text_snippet': None,
                            'status': 'failed',
                            'error': str(e)
                        }
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

    def _extract_text(self, html: str) -> str:
        """Extract main text content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = ' '.join(text.split())

        # Truncate to max length
        if len(text) > settings.MAX_WEBSITE_TEXT_LENGTH:
            text = text[:settings.MAX_WEBSITE_TEXT_LENGTH] + "..."

        return text

async def scrape_companies(domains: List[str]) -> List[Dict]:
    """Scrape multiple company websites concurrently"""
    scraper = WebsiteScraper()
    tasks = [scraper.fetch_website(domain) for domain in domains]
    results = await asyncio.gather(*tasks)
    return results
```

---

### 5. Processing Layer

#### 5.1 Data Cleaning (`src/processing/cleaning.py`)

**Purpose:** Join and clean structured + unstructured data

```python
from typing import List, Dict

def merge_structured_unstructured(
    structured_data: List[Dict],
    scraped_data: List[Dict]
) -> List[Dict]:
    """
    Merge structured company data with scraped website content

    Returns list of enrichment-ready company records
    """
    # Create lookup dict for scraped data
    scraped_lookup = {item['domain']: item for item in scraped_data}

    merged = []
    for company in structured_data:
        domain = company['domain']
        scraped = scraped_lookup.get(domain, {})

        merged_company = {
            **company,
            'website_text_snippet': scraped.get('text_snippet'),
            'scraping_status': scraped.get('status', 'failed'),
            'scraping_error': scraped.get('error')
        }
        merged.append(merged_company)

    return merged
```

#### 5.2 LLM Enrichment Chain (`src/processing/llm_chain.py`)

**Purpose:** LangChain-based LLM enrichment pipeline

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional
from src.config import settings
import logging

logger = logging.getLogger(__name__)

# Define expected output schema
class CompanyEnrichment(BaseModel):
    icp_fit_score: int = Field(description="ICP fit score from 0-100")
    segment: str = Field(description="Company segment: SMB, Mid-Market, or Enterprise")
    primary_use_case: str = Field(description="Primary use case for AI automation")
    risk_flags: List[str] = Field(description="List of potential risks or concerns")
    personalized_pitch: str = Field(description="One-sentence personalized sales pitch")

# Create output parser
output_parser = JsonOutputParser(pydantic_object=CompanyEnrichment)

# Define prompt template
ENRICHMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert B2B sales analyst specializing in AI automation platforms.

Your task is to analyze a company and determine how well it fits the Ideal Customer Profile (ICP) for an AI automation platform that helps businesses:
- Automate repetitive workflows
- Integrate disparate systems
- Enhance data-driven decision making
- Improve operational efficiency

Provide your analysis in the following JSON format:
{format_instructions}
"""),
    ("human", """Analyze this company:

Company Name: {company_name}
Domain: {domain}
Country: {country}
Employee Count: {employee_count}
Industry: {industry_raw}

Website Content:
{website_text}

Provide a thorough ICP fit analysis.""")
])

class LLMEnricher:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )
        self.chain = ENRICHMENT_PROMPT | self.llm | output_parser

    async def enrich_company(self, company_data: dict) -> dict:
        """
        Enrich a single company using LLM

        Returns enriched data or error info
        """
        try:
            # Prepare input
            website_text = company_data.get('website_text_snippet', 'No website content available')

            # Invoke chain
            result = await self.chain.ainvoke({
                'company_name': company_data['company_name'],
                'domain': company_data['domain'],
                'country': company_data['country'],
                'employee_count': company_data['employee_count'],
                'industry_raw': company_data['industry_raw'],
                'website_text': website_text,
                'format_instructions': output_parser.get_format_instructions()
            })

            return {
                **company_data,
                'icp_fit_score': result['icp_fit_score'],
                'segment': result['segment'],
                'primary_use_case': result['primary_use_case'],
                'risk_flags': result['risk_flags'],
                'personalized_pitch': result['personalized_pitch'],
                'enrichment_status': 'success',
                'enrichment_error': None
            }

        except Exception as e:
            logger.error(f"LLM enrichment failed for {company_data.get('domain')}: {e}")
            return {
                **company_data,
                'enrichment_status': 'failed',
                'enrichment_error': str(e)
            }
```

---

### 6. API Layer (`src/api/main.py`)

**Purpose:** FastAPI REST API for querying enriched companies

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from src.db import get_db
from src.models import Company
from src.schemas import CompanyEnriched, CompanyListResponse
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CommonForge Lead Scoring API",
    description="AI-powered B2B lead scoring and enrichment",
    version="1.0.0"
)

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "commonforge-api"}

@app.get("/companies", response_model=CompanyListResponse, tags=["Companies"])
async def list_companies(
    min_score: int = Query(0, ge=0, le=100, description="Minimum ICP fit score"),
    country: Optional[str] = Query(None, description="Filter by country"),
    segment: Optional[str] = Query(None, description="Filter by segment"),
    db: Session = Depends(get_db)
):
    """
    List enriched companies with optional filtering
    """
    query = db.query(Company).filter(Company.enrichment_status == "success")

    # Apply filters
    if min_score > 0:
        query = query.filter(Company.icp_fit_score >= min_score)

    if country:
        query = query.filter(Company.country == country)

    if segment:
        if segment not in ["SMB", "Mid-Market", "Enterprise"]:
            raise HTTPException(status_code=400, detail="Invalid segment")
        query = query.filter(Company.segment == segment)

    # Execute query
    companies = query.order_by(Company.icp_fit_score.desc()).all()

    return CompanyListResponse(
        total=len(companies),
        companies=companies
    )

@app.get("/companies/{company_id}", response_model=CompanyEnriched, tags=["Companies"])
async def get_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single enriched company by ID
    """
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company
```

---

## Data Flow

### End-to-End Pipeline Flow

```
1. LOAD CSV
   └─> pandas.read_csv()
   └─> Validation & cleaning
   └─> List[Dict] of structured data

2. SCRAPE WEBSITES (Async)
   └─> For each domain in parallel:
       ├─> httpx.AsyncClient.get()
       ├─> BeautifulSoup parsing
       └─> Text extraction & truncation
   └─> List[Dict] of scraped data

3. MERGE DATA
   └─> Join structured + unstructured by domain
   └─> List[Dict] of enrichment-ready records

4. LLM ENRICHMENT (Async with rate limiting)
   └─> For each company (with concurrency limit):
       ├─> Format prompt with company data
       ├─> LangChain chain.ainvoke()
       ├─> Parse JSON output
       └─> Validate with Pydantic
   └─> List[Dict] of enriched records

5. PERSIST TO DATABASE
   └─> For each enriched record:
       ├─> Create SQLAlchemy Company object
       ├─> Upsert by domain (update if exists)
       └─> Commit transaction
   └─> Database persisted

6. QUERY VIA API
   └─> FastAPI endpoints
   └─> SQLAlchemy queries
   └─> Pydantic serialization
   └─> JSON response
```

---

## Security Considerations

### 1. API Keys & Secrets
- Store in `.env` file (never commit)
- Use environment variables in production
- Rotate keys regularly

### 2. Database Security
- Use connection pooling
- Parameterized queries (SQLAlchemy ORM)
- No raw SQL execution
- Principle of least privilege for DB user

### 3. Web Scraping Ethics
- Respect robots.txt
- Implement rate limiting
- Use appropriate User-Agent
- Handle failures gracefully

### 4. API Security
- Input validation (Pydantic)
- SQL injection prevention (ORM)
- Rate limiting (future: add middleware)
- CORS configuration

### 5. Data Privacy
- No PII stored beyond business data
- Secure database connections (SSL)
- Audit logging for data access

---

## Scalability & Performance

### Current Scale: Prototype (5-100 companies)
- **Async scraping:** 5-10 concurrent requests
- **LLM calls:** 3 concurrent requests (rate limiting)
- **Database:** Single PostgreSQL instance
- **API:** Single FastAPI process

### Future Scale: Production (1000s-10000s companies)

#### Horizontal Scaling
1. **Pipeline workers:** Celery/RQ with Redis
2. **API instances:** Load-balanced FastAPI containers
3. **Database:** Read replicas, connection pooling

#### Optimization Strategies
1. **Caching:**
   - Cache scraped website content (Redis)
   - Cache LLM responses by domain
   - API response caching

2. **Batching:**
   - Batch LLM requests where possible
   - Bulk database inserts

3. **Queueing:**
   - Job queue for enrichment pipeline
   - Priority queues for high-value leads

4. **Monitoring:**
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)

---

## Conclusion

This architecture provides:
- ✅ Clear separation of concerns
- ✅ Async operations for performance
- ✅ Type safety throughout
- ✅ Resilient error handling
- ✅ Scalability pathway
- ✅ Production-ready patterns

The modular design allows each component to be developed, tested, and scaled independently.
