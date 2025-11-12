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
