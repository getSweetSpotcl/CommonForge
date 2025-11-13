"""
End-to-end ingestion test combining CSV and web scraping.
"""

import asyncio
from pathlib import Path
from src.ingestion.structured import load_companies_from_csv
from src.ingestion.unstructured import scrape_companies


async def test_full_ingestion():
    """Test complete ingestion pipeline"""

    print("=" * 60)
    print("FULL INGESTION TEST")
    print("=" * 60)

    # Step 1: Load structured data
    print("\n1. Loading structured data from CSV...")
    csv_path = Path("data/companies.csv")
    companies = load_companies_from_csv(csv_path)
    print(f"   ✓ Loaded {len(companies)} companies")

    # Step 2: Scrape websites
    print("\n2. Scraping company websites...")
    domains = [c["domain"] for c in companies]
    scraped_data = await scrape_companies(domains)

    successful_scrapes = sum(1 for s in scraped_data if s["status"] == "success")
    print(f"   ✓ Scraped {successful_scrapes}/{len(domains)} websites successfully")

    # Step 3: Merge data
    print("\n3. Merging structured and unstructured data...")
    scraped_lookup = {s["domain"]: s for s in scraped_data}

    enriched_companies = []
    for company in companies:
        scraped = scraped_lookup.get(company["domain"], {})

        enriched = {
            **company,
            "website_text_snippet": scraped.get("text_snippet"),
            "scraping_status": scraped.get("status", "failed"),
            "scraping_error": scraped.get("error"),
        }
        enriched_companies.append(enriched)

    print(f"   ✓ Merged data for {len(enriched_companies)} companies")

    # Step 4: Display results
    print("\n4. Sample results:")
    print("=" * 60)

    for company in enriched_companies[:3]:  # Show first 3
        print(f"\nCompany: {company['company_name']}")
        print(f"Domain: {company['domain']}")
        print(f"Country: {company['country']}")
        print(f"Employees: {company['employee_count']:,}")
        print(f"Scraping: {company['scraping_status']}")

        if company["website_text_snippet"]:
            snippet = company["website_text_snippet"][:150]
            print(f"Text: {snippet}...")

    print("\n" + "=" * 60)
    print("✅ FULL INGESTION TEST COMPLETE")
    print("=" * 60)

    return enriched_companies


if __name__ == "__main__":
    asyncio.run(test_full_ingestion())
