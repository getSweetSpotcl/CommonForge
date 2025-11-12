# Phase 2: Data Layer & Models

**Duration:** 2-3 hours
**Priority:** Critical - Required by all other components
**Dependencies:** Phase 1 (Project Setup)

---

## Objectives

1. Implement configuration management system
2. Set up database connection and session management
3. Create SQLAlchemy ORM models
4. Define Pydantic schemas for API
5. Create database initialization utilities
6. Test database connectivity

---

## Task Checklist

### 2.1 Implement Configuration Management (`src/config.py`)

**Purpose:** Centralized, type-safe configuration using Pydantic Settings

**Implementation:**

```python
"""
Configuration management for CommonForge.

Uses Pydantic Settings to load and validate environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DATABASE_URL: str

    # OpenAI/LLM Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 1000

    # Web Scraping Configuration
    SCRAPER_TIMEOUT: int = 10
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_USER_AGENT: str = "CommonForge Lead Scorer/1.0"

    # Processing Configuration
    MAX_WEBSITE_TEXT_LENGTH: int = 3000
    CONCURRENT_LLM_CALLS: int = 3

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only load settings once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
```

**Test Configuration:**

```python
# Quick test to verify configuration loads
if __name__ == "__main__":
    from src.config import settings

    print("Configuration loaded successfully!")
    print(f"Database URL: {settings.DATABASE_URL[:20]}...")
    print(f"OpenAI Model: {settings.OPENAI_MODEL}")
    print(f"Log Level: {settings.LOG_LEVEL}")
```

**Run test:**
```bash
python -m src.config
```

---

### 2.2 Implement Database Connection (`src/db.py`)

**Purpose:** SQLAlchemy engine, session management, and connection utilities

**Implementation:**

```python
"""
Database connection and session management.

Provides SQLAlchemy engine, session factory, and Base class for ORM models.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from src.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
)


# Add connection event listeners for debugging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new database connection is created"""
    logger.debug("Database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool"""
    logger.debug("Connection checked out from pool")


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Session: SQLAlchemy database session

    The session is automatically closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in ORM models.
    Safe to run multiple times (only creates missing tables).
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")


def drop_all_tables() -> None:
    """
    Drop all database tables.

    WARNING: This is destructive and will delete all data!
    Only use in development/testing.
    """
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


def check_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
```

**Test Database Connection:**

```python
# Quick test to verify database connection
if __name__ == "__main__":
    from src.db import check_connection, init_db

    print("Testing database connection...")
    if check_connection():
        print("✓ Database connection successful")
        print("\nInitializing database tables...")
        init_db()
        print("✓ Database tables initialized")
    else:
        print("✗ Database connection failed")
        print("Check your DATABASE_URL in .env")
```

**Run test:**
```bash
python -m src.db
```

---

### 2.3 Create ORM Models (`src/models.py`)

**Purpose:** Define database schema using SQLAlchemy ORM

**Implementation:**

```python
"""
SQLAlchemy ORM models for CommonForge.

Defines the database schema and relationships.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    Index,
)
from sqlalchemy.sql import func
from typing import List, Optional
import json

from src.db import Base


class Company(Base):
    """
    Company model storing structured, unstructured, and enriched data.

    Attributes:
        id: Primary key
        company_name: Official company name
        domain: Company website domain (unique)
        country: Country of operation
        employee_count: Number of employees
        industry_raw: Industry category

        website_text_snippet: Extracted text from company website
        scraping_status: Status of web scraping (pending/success/failed)
        scraping_error: Error message if scraping failed

        icp_fit_score: AI-generated ICP fit score (0-100)
        segment: Company segment (SMB/Mid-Market/Enterprise)
        primary_use_case: Main use case for AI automation
        risk_flags: List of potential risks (stored as JSON)
        personalized_pitch: AI-generated sales pitch
        enrichment_status: Status of LLM enrichment (pending/success/failed)
        enrichment_error: Error message if enrichment failed

        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "companies"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Structured Data (from CSV)
    company_name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    country = Column(String(100), nullable=False, index=True)
    employee_count = Column(Integer, nullable=False)
    industry_raw = Column(String(255), nullable=False)

    # Unstructured Data (from web scraping)
    website_text_snippet = Column(Text, nullable=True)
    scraping_status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )
    scraping_error = Column(Text, nullable=True)

    # Enriched Data (from LLM)
    icp_fit_score = Column(Integer, nullable=True, index=True)
    segment = Column(String(50), nullable=True, index=True)
    primary_use_case = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    personalized_pitch = Column(Text, nullable=True)
    enrichment_status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )
    enrichment_error = Column(Text, nullable=True)

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True
    )

    def __repr__(self) -> str:
        """String representation of Company"""
        return (
            f"<Company("
            f"id={self.id}, "
            f"name='{self.company_name}', "
            f"score={self.icp_fit_score}"
            f")>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "domain": self.domain,
            "country": self.country,
            "employee_count": self.employee_count,
            "industry_raw": self.industry_raw,
            "website_text_snippet": self.website_text_snippet,
            "scraping_status": self.scraping_status,
            "icp_fit_score": self.icp_fit_score,
            "segment": self.segment,
            "primary_use_case": self.primary_use_case,
            "risk_flags": self.risk_flags,
            "personalized_pitch": self.personalized_pitch,
            "enrichment_status": self.enrichment_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Additional indexes for common queries
Index("idx_company_score_segment", Company.icp_fit_score, Company.segment)
Index("idx_company_country_segment", Company.country, Company.segment)
```

**Database Schema Diagram:**

```
┌─────────────────────────────────────────────────────────┐
│                        companies                        │
├─────────────────────────────────────────────────────────┤
│ PK  id                    INTEGER                       │
│     company_name          VARCHAR(255)     [indexed]    │
│ UQ  domain                VARCHAR(255)     [indexed]    │
│     country               VARCHAR(100)     [indexed]    │
│     employee_count        INTEGER                       │
│     industry_raw          VARCHAR(255)                  │
│     website_text_snippet  TEXT                          │
│     scraping_status       VARCHAR(50)      [indexed]    │
│     scraping_error        TEXT                          │
│     icp_fit_score         INTEGER          [indexed]    │
│     segment               VARCHAR(50)      [indexed]    │
│     primary_use_case      TEXT                          │
│     risk_flags            JSON                          │
│     personalized_pitch    TEXT                          │
│     enrichment_status     VARCHAR(50)      [indexed]    │
│     enrichment_error      TEXT                          │
│     created_at            TIMESTAMP                     │
│     updated_at            TIMESTAMP                     │
└─────────────────────────────────────────────────────────┘

Composite Indexes:
- (icp_fit_score, segment)
- (country, segment)
```

---

### 2.4 Create Pydantic Schemas (`src/schemas.py`)

**Purpose:** Define API request/response models with validation

**Implementation:**

```python
"""
Pydantic schemas for API request/response validation.

These schemas ensure data validation and provide automatic
OpenAPI documentation for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class CompanyBase(BaseModel):
    """Base schema with common company fields"""

    company_name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    country: str = Field(..., min_length=1, max_length=100)
    employee_count: int = Field(..., gt=0)
    industry_raw: str = Field(..., min_length=1, max_length=255)


class CompanyCreate(CompanyBase):
    """Schema for creating a new company"""

    website_text_snippet: Optional[str] = None


class CompanyEnriched(CompanyBase):
    """Schema for enriched company with all fields"""

    id: int
    website_text_snippet: Optional[str] = None
    scraping_status: str

    icp_fit_score: Optional[int] = Field(None, ge=0, le=100)
    segment: Optional[str] = None
    primary_use_case: Optional[str] = None
    risk_flags: Optional[List[str]] = None
    personalized_pitch: Optional[str] = None
    enrichment_status: str

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Enable ORM mode

    @validator("segment")
    def validate_segment(cls, v):
        """Validate segment is one of the allowed values"""
        if v and v not in ["SMB", "Mid-Market", "Enterprise"]:
            raise ValueError("Segment must be SMB, Mid-Market, or Enterprise")
        return v


class CompanyListResponse(BaseModel):
    """Response schema for list of companies"""

    total: int = Field(..., ge=0)
    companies: List[CompanyEnriched]


class CompanyQuery(BaseModel):
    """Schema for query parameters"""

    min_score: int = Field(0, ge=0, le=100, description="Minimum ICP fit score")
    country: Optional[str] = Field(None, max_length=100, description="Filter by country")
    segment: Optional[str] = Field(None, description="Filter by segment")

    @validator("segment")
    def validate_segment(cls, v):
        """Validate segment parameter"""
        if v and v not in ["SMB", "Mid-Market", "Enterprise"]:
            raise ValueError("Segment must be SMB, Mid-Market, or Enterprise")
        return v


class HealthCheck(BaseModel):
    """Health check response schema"""

    status: str
    service: str
    database: Optional[bool] = None
```

---

### 2.5 Create Database Initialization Script

**File:** `scripts/init_db.sh`

```bash
#!/bin/bash
# Database initialization script for CommonForge

set -e  # Exit on error

echo "🔧 Initializing CommonForge database..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "   Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
source .env

# Extract database name from DATABASE_URL
DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo "📦 Database: $DB_NAME"

# Check if PostgreSQL is running
if ! pg_isready > /dev/null 2>&1; then
    echo "❌ Error: PostgreSQL is not running"
    echo "   Start PostgreSQL and try again"
    exit 1
fi

echo "✓ PostgreSQL is running"

# Create database if it doesn't exist
if ! psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "📦 Creating database: $DB_NAME"
    createdb $DB_NAME
    echo "✓ Database created"
else
    echo "✓ Database already exists"
fi

# Initialize tables using Python
echo "📊 Creating database tables..."
python -m src.db

echo "✅ Database initialization complete!"
```

**Make executable:**
```bash
chmod +x scripts/init_db.sh
```

---

## Verification Steps

### 2.6 Verify Configuration

```bash
# Test configuration loading
python -m src.config

# Expected output:
# Configuration loaded successfully!
# Database URL: postgresql+psycopg...
# OpenAI Model: gpt-4-turbo-preview
# Log Level: INFO
```

### 2.7 Verify Database Connection

```bash
# Test database connection
python -m src.db

# Expected output:
# Testing database connection...
# ✓ Database connection successful
#
# Initializing database tables...
# ✓ Database tables initialized
```

### 2.8 Verify Database Schema

```bash
# Connect to database and check tables
psql $DATABASE_URL -c "\dt"

# Expected output:
#          List of relations
#  Schema |   Name    | Type  |  Owner
# --------+-----------+-------+---------
#  public | companies | table | <user>
```

```bash
# Check table structure
psql $DATABASE_URL -c "\d companies"

# Should show all columns and indexes
```

### 2.9 Test ORM Model

Create a test script: `tests/test_models.py`

```python
"""Test database models"""

from src.db import SessionLocal, init_db
from src.models import Company


def test_create_company():
    """Test creating a company record"""
    init_db()

    db = SessionLocal()
    try:
        # Create test company
        company = Company(
            company_name="Test Corp",
            domain="test.com",
            country="USA",
            employee_count=100,
            industry_raw="Technology",
            scraping_status="pending",
            enrichment_status="pending",
        )

        db.add(company)
        db.commit()
        db.refresh(company)

        print(f"✓ Created company: {company}")
        print(f"  ID: {company.id}")
        print(f"  Name: {company.company_name}")

        # Query it back
        queried = db.query(Company).filter_by(domain="test.com").first()
        assert queried is not None
        assert queried.company_name == "Test Corp"
        print("✓ Successfully queried company")

        # Clean up
        db.delete(company)
        db.commit()
        print("✓ Test cleanup complete")

    finally:
        db.close()


if __name__ == "__main__":
    test_create_company()
```

**Run test:**
```bash
python tests/test_models.py
```

---

## Common Issues & Solutions

### Issue 1: Database Connection Error

**Error:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution:**
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

### Issue 2: Database Does Not Exist

**Error:** `sqlalchemy.exc.OperationalError: database "commonforge" does not exist`

**Solution:**
```bash
# Create the database
createdb commonforge

# Or run init script
./scripts/init_db.sh
```

### Issue 3: Invalid DATABASE_URL

**Error:** `pydantic.error_wrappers.ValidationError: DATABASE_URL`

**Solution:**
- Check `.env` file exists
- Verify DATABASE_URL format: `postgresql+psycopg2://user:pass@host:port/dbname`
- Ensure credentials are correct

---

## Success Criteria

After completing Phase 2, you should have:

- ✅ `src/config.py` with working configuration management
- ✅ `src/db.py` with database connection and session management
- ✅ `src/models.py` with Company ORM model
- ✅ `src/schemas.py` with Pydantic validation schemas
- ✅ Database tables created in PostgreSQL
- ✅ Successful test of creating and querying a company record

---

## Next Steps

Once Phase 2 is complete:
1. Verify all database operations work correctly
2. Test configuration loading from `.env`
3. Proceed to **Phase 3: Data Ingestion Layer**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Implement config.py | 20 min |
| Implement db.py | 30 min |
| Create models.py | 40 min |
| Create schemas.py | 30 min |
| Write initialization script | 20 min |
| Testing and verification | 30 min |
| **Total** | **2.5 hours** |
