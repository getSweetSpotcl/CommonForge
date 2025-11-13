"""
Data cleaning and merging utilities.

Combines structured CSV data with unstructured web scraping results.
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def merge_structured_unstructured(
    structured_data: List[Dict], scraped_data: List[Dict]
) -> List[Dict]:
    """
    Merge structured CSV data with unstructured scraped data.

    Args:
        structured_data: List of company dicts from CSV
        scraped_data: List of scraping result dicts

    Returns:
        List[Dict]: Merged company data ready for enrichment

    Example:
        >>> csv_companies = load_companies_from_csv('data/companies.csv')
        >>> scraped = await scrape_companies(domains)
        >>> merged = merge_structured_unstructured(csv_companies, scraped)
    """
    logger.info(
        f"Merging {len(structured_data)} structured records "
        f"with {len(scraped_data)} scraped records"
    )

    # Create lookup dictionary by domain
    scraped_lookup = {result["domain"]: result for result in scraped_data}

    merged_companies = []

    for company in structured_data:
        domain = company["domain"]
        scraped_result = scraped_lookup.get(domain, {})

        # Merge data
        merged = {
            # Structured data (from CSV)
            "company_name": company["company_name"],
            "domain": company["domain"],
            "country": company["country"],
            "employee_count": company["employee_count"],
            "industry_raw": company["industry_raw"],
            # Unstructured data (from scraping)
            "website_text_snippet": scraped_result.get("text_snippet"),
            "scraping_status": scraped_result.get("status", "not_attempted"),
            "scraping_error": scraped_result.get("error"),
            # Initialize enrichment fields
            "icp_fit_score": None,
            "segment": None,
            "primary_use_case": None,
            "risk_flags": None,
            "personalized_pitch": None,
            "enrichment_status": "pending",
            "enrichment_error": None,
        }

        merged_companies.append(merged)

    successful_scrapes = sum(1 for c in merged_companies if c["scraping_status"] == "success")

    logger.info(
        f"Merged {len(merged_companies)} companies "
        f"({successful_scrapes} with successful scrapes)"
    )

    return merged_companies


def prepare_for_enrichment(merged_data: List[Dict]) -> List[Dict]:
    """
    Prepare merged data for LLM enrichment.

    Filters out companies without website data and formats
    input for the LLM chain.

    Args:
        merged_data: List of merged company dicts

    Returns:
        List[Dict]: Companies ready for enrichment

    Example:
        >>> merged = merge_structured_unstructured(csv_data, scraped_data)
        >>> ready = prepare_for_enrichment(merged)
    """
    logger.info(f"Preparing {len(merged_data)} companies for enrichment")

    # Filter companies that have website text
    enrichable = [
        company
        for company in merged_data
        if company["scraping_status"] == "success" and company["website_text_snippet"]
    ]

    # Mark companies without website data as failed
    for company in merged_data:
        if company["scraping_status"] != "success":
            company["enrichment_status"] = "skipped"
            company[
                "enrichment_error"
            ] = f"Skipped due to scraping status: {company['scraping_status']}"

    logger.info(
        f"{len(enrichable)} companies ready for enrichment "
        f"({len(merged_data) - len(enrichable)} skipped)"
    )

    return enrichable


def validate_enrichment_result(result: Dict) -> bool:
    """
    Validate that an enrichment result has required fields.

    Args:
        result: Enrichment result from LLM

    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = [
        "icp_fit_score",
        "segment",
        "primary_use_case",
        "risk_flags",
        "personalized_pitch",
    ]

    for field in required_fields:
        if field not in result:
            logger.warning(f"Missing required field: {field}")
            return False

    # Validate score range
    if not isinstance(result["icp_fit_score"], int):
        logger.warning("icp_fit_score must be an integer")
        return False

    if not (0 <= result["icp_fit_score"] <= 100):
        logger.warning("icp_fit_score must be between 0 and 100")
        return False

    # Validate segment
    valid_segments = ["SMB", "Mid-Market", "Enterprise"]
    if result["segment"] not in valid_segments:
        logger.warning(f"Invalid segment: {result['segment']}")
        return False

    # Validate risk_flags is list
    if not isinstance(result["risk_flags"], list):
        logger.warning("risk_flags must be a list")
        return False

    return True


def apply_enrichment_result(company: Dict, enrichment: Dict) -> Dict:
    """
    Apply enrichment result to company data.

    Args:
        company: Company dict to enrich
        enrichment: Enrichment result from LLM

    Returns:
        Dict: Enriched company data
    """
    company_copy = company.copy()

    # Apply enrichment fields
    company_copy["icp_fit_score"] = enrichment.get("icp_fit_score")
    company_copy["segment"] = enrichment.get("segment")
    company_copy["primary_use_case"] = enrichment.get("primary_use_case")
    company_copy["risk_flags"] = enrichment.get("risk_flags")
    company_copy["personalized_pitch"] = enrichment.get("personalized_pitch")
    company_copy["enrichment_status"] = "success"
    company_copy["enrichment_error"] = None

    return company_copy


# Test script
if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.ingestion.structured import load_companies_from_csv
    from src.ingestion.unstructured import scrape_companies

    async def test_cleaning():
        print("=" * 60)
        print("DATA CLEANING TEST")
        print("=" * 60)

        # Load CSV data
        print("\n1. Loading CSV data...")
        csv_path = Path("data/companies.csv")
        structured = load_companies_from_csv(csv_path)
        print(f"   ✓ Loaded {len(structured)} companies from CSV")

        # Scrape websites
        print("\n2. Scraping websites...")
        domains = [c["domain"] for c in structured]
        scraped = await scrape_companies(domains)
        print(f"   ✓ Scraped {len(scraped)} websites")

        # Merge data
        print("\n3. Merging data...")
        merged = merge_structured_unstructured(structured, scraped)
        print(f"   ✓ Merged {len(merged)} companies")

        # Prepare for enrichment
        print("\n4. Preparing for enrichment...")
        ready = prepare_for_enrichment(merged)
        print(f"   ✓ {len(ready)} companies ready for enrichment")

        # Display sample
        print("\n5. Sample merged data:")
        print("=" * 60)
        for company in merged[:2]:
            print(f"\nCompany: {company['company_name']}")
            print(f"Domain: {company['domain']}")
            print(f"Scraping: {company['scraping_status']}")
            print(f"Enrichment: {company['enrichment_status']}")
            if company["website_text_snippet"]:
                snippet = company["website_text_snippet"][:100]
                print(f"Text: {snippet}...")

        print("\n" + "=" * 60)
        print("✅ DATA CLEANING TEST COMPLETE")
        print("=" * 60)

    asyncio.run(test_cleaning())
