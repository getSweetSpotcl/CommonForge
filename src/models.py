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
from typing import Optional

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
    scraping_status = Column(String(50), nullable=False, default="pending", index=True)
    scraping_error = Column(Text, nullable=True)

    # Enriched Data (from LLM)
    icp_fit_score = Column(Integer, nullable=True, index=True)
    segment = Column(String(50), nullable=True, index=True)
    primary_use_case = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    personalized_pitch = Column(Text, nullable=True)
    enrichment_status = Column(String(50), nullable=False, default="pending", index=True)
    enrichment_error = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

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
