"""
Tests for data processing layer (cleaning and LLM enrichment).
"""

import pytest
from pathlib import Path
from src.processing.cleaning import (
    merge_structured_unstructured,
    prepare_for_enrichment,
    validate_enrichment_result,
    apply_enrichment_result,
)
from src.processing.llm_chain import CompanyEnrichment, LLMEnricher


class TestDataCleaning:
    """Tests for data cleaning utilities"""

    def test_merge_structured_unstructured(self):
        """Test merging CSV and scraped data"""
        structured = [
            {
                "company_name": "Test Corp",
                "domain": "test.com",
                "country": "USA",
                "employee_count": 100,
                "industry_raw": "Software",
            }
        ]

        scraped = [
            {
                "domain": "test.com",
                "text_snippet": "We build software",
                "status": "success",
                "error": None,
            }
        ]

        merged = merge_structured_unstructured(structured, scraped)

        assert len(merged) == 1
        assert merged[0]["company_name"] == "Test Corp"
        assert merged[0]["website_text_snippet"] == "We build software"
        assert merged[0]["scraping_status"] == "success"
        assert merged[0]["enrichment_status"] == "pending"

    def test_merge_with_failed_scrape(self):
        """Test merging when scraping failed"""
        structured = [
            {
                "company_name": "Test Corp",
                "domain": "test.com",
                "country": "USA",
                "employee_count": 100,
                "industry_raw": "Software",
            }
        ]

        scraped = [
            {"domain": "test.com", "text_snippet": None, "status": "failed", "error": "Timeout"}
        ]

        merged = merge_structured_unstructured(structured, scraped)

        assert len(merged) == 1
        assert merged[0]["website_text_snippet"] is None
        assert merged[0]["scraping_status"] == "failed"
        assert merged[0]["scraping_error"] == "Timeout"

    def test_prepare_for_enrichment(self):
        """Test filtering companies ready for enrichment"""
        merged = [
            {
                "company_name": "Good Corp",
                "domain": "good.com",
                "scraping_status": "success",
                "website_text_snippet": "Some text",
                "enrichment_status": "pending",
            },
            {
                "company_name": "Bad Corp",
                "domain": "bad.com",
                "scraping_status": "failed",
                "website_text_snippet": None,
                "enrichment_status": "pending",
            },
        ]

        ready = prepare_for_enrichment(merged)

        assert len(ready) == 1
        assert ready[0]["company_name"] == "Good Corp"

        # Check that bad corp was marked as skipped
        assert merged[1]["enrichment_status"] == "skipped"
        assert "scraping status" in merged[1]["enrichment_error"]

    def test_validate_enrichment_result_valid(self):
        """Test validation of valid enrichment result"""
        result = {
            "icp_fit_score": 85,
            "segment": "Mid-Market",
            "primary_use_case": "Sales automation",
            "risk_flags": [],
            "personalized_pitch": "Great fit for your team",
        }

        assert validate_enrichment_result(result) is True

    def test_validate_enrichment_result_missing_field(self):
        """Test validation fails with missing field"""
        result = {
            "icp_fit_score": 85,
            "segment": "Mid-Market",
            # Missing other fields
        }

        assert validate_enrichment_result(result) is False

    def test_validate_enrichment_result_invalid_score(self):
        """Test validation fails with invalid score"""
        result = {
            "icp_fit_score": 150,  # Invalid: > 100
            "segment": "Mid-Market",
            "primary_use_case": "Sales automation",
            "risk_flags": [],
            "personalized_pitch": "Great fit",
        }

        assert validate_enrichment_result(result) is False

    def test_validate_enrichment_result_invalid_segment(self):
        """Test validation fails with invalid segment"""
        result = {
            "icp_fit_score": 85,
            "segment": "InvalidSegment",
            "primary_use_case": "Sales automation",
            "risk_flags": [],
            "personalized_pitch": "Great fit",
        }

        assert validate_enrichment_result(result) is False

    def test_apply_enrichment_result(self):
        """Test applying enrichment to company"""
        company = {
            "company_name": "Test Corp",
            "domain": "test.com",
            "icp_fit_score": None,
            "enrichment_status": "pending",
        }

        enrichment = {
            "icp_fit_score": 85,
            "segment": "Mid-Market",
            "primary_use_case": "Sales automation",
            "risk_flags": ["Budget concerns"],
            "personalized_pitch": "Perfect fit",
        }

        enriched = apply_enrichment_result(company, enrichment)

        assert enriched["icp_fit_score"] == 85
        assert enriched["segment"] == "Mid-Market"
        assert enriched["enrichment_status"] == "success"
        assert enriched["enrichment_error"] is None


class TestLLMEnrichment:
    """Tests for LLM enrichment"""

    def test_company_enrichment_schema(self):
        """Test CompanyEnrichment schema validation"""
        # Valid data
        data = {
            "icp_fit_score": 85,
            "segment": "Mid-Market",
            "primary_use_case": "Sales automation",
            "risk_flags": [],
            "personalized_pitch": "Great fit for your team",
        }

        enrichment = CompanyEnrichment(**data)
        assert enrichment.icp_fit_score == 85
        assert enrichment.segment == "Mid-Market"

    def test_company_enrichment_schema_invalid_score(self):
        """Test schema rejects invalid scores"""
        data = {
            "icp_fit_score": 150,  # Invalid
            "segment": "Mid-Market",
            "primary_use_case": "Sales automation",
            "risk_flags": [],
            "personalized_pitch": "Great fit",
        }

        with pytest.raises(Exception):  # Pydantic ValidationError
            CompanyEnrichment(**data)

    def test_company_enrichment_schema_invalid_segment(self):
        """Test schema rejects invalid segments"""
        data = {
            "icp_fit_score": 85,
            "segment": "InvalidSegment",
            "primary_use_case": "Sales automation",
            "risk_flags": [],
            "personalized_pitch": "Great fit",
        }

        with pytest.raises(Exception):  # Pydantic ValidationError
            CompanyEnrichment(**data)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip by default (requires OpenAI API key)
        reason="Requires OpenAI API key and makes real API calls",
    )
    async def test_enrich_company_real(self):
        """Test enriching a real company (manual test with API key)"""
        from src.ingestion.structured import load_companies_from_csv
        from src.ingestion.unstructured import scrape_companies
        from src.processing.cleaning import merge_structured_unstructured

        # Load real data
        csv_path = Path("data/companies.csv")
        structured = load_companies_from_csv(csv_path)
        domains = [c["domain"] for c in structured[:1]]  # Test with first company
        scraped = await scrape_companies(domains)

        # Merge
        merged = merge_structured_unstructured(structured[:1], scraped)

        # Enrich
        enricher = LLMEnricher()
        result = await enricher.enrich_company(merged[0])

        # Validate
        assert 0 <= result["icp_fit_score"] <= 100
        assert result["segment"] in ["SMB", "Mid-Market", "Enterprise"]
        assert len(result["personalized_pitch"]) > 0

    def test_llm_enricher_initialization(self):
        """Test LLMEnricher initialization"""
        enricher = LLMEnricher(temperature=0.5, max_tokens=500)

        assert enricher.temperature == 0.5
        assert enricher.max_tokens == 500
        assert enricher.llm is not None
        assert enricher.parser is not None


# Integration test
@pytest.mark.asyncio
async def test_full_processing_pipeline():
    """Test complete processing pipeline (CSV -> scrape -> clean -> prepare)"""
    from src.ingestion.structured import load_companies_from_csv
    from src.ingestion.unstructured import scrape_companies

    # Load CSV
    csv_path = Path("data/companies.csv")
    structured = load_companies_from_csv(csv_path)
    assert len(structured) > 0

    # Scrape (just first company for speed)
    domains = [structured[0]["domain"]]
    scraped = await scrape_companies(domains)
    assert len(scraped) == 1

    # Merge
    merged = merge_structured_unstructured(structured[:1], scraped)
    assert len(merged) == 1
    assert "website_text_snippet" in merged[0]
    assert "enrichment_status" in merged[0]

    # Prepare for enrichment
    ready = prepare_for_enrichment(merged)

    # Should have at least one company ready (if scraping succeeded)
    if merged[0]["scraping_status"] == "success":
        assert len(ready) >= 1
        assert ready[0]["website_text_snippet"] is not None
