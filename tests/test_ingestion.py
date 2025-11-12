"""
Tests for data ingestion layer.
"""

import pytest
from pathlib import Path
from src.ingestion.structured import load_companies_from_csv, CSVIngestor
from src.ingestion.unstructured import scrape_companies, WebsiteScraper


class TestStructuredIngestion:
    """Tests for CSV ingestion"""

    def test_load_companies_csv(self):
        """Test loading sample CSV"""
        csv_path = Path("data/companies.csv")
        companies = load_companies_from_csv(csv_path)

        assert len(companies) > 0
        assert all('company_name' in c for c in companies)
        assert all('domain' in c for c in companies)

    def test_domain_normalization(self):
        """Test domain normalization"""
        test_cases = [
            ('HTTP://WWW.EXAMPLE.COM', 'example.com'),
            ('https://example.com/', 'example.com'),
            ('www.example.com', 'example.com'),
            ('example.com:8080', 'example.com'),
            ('example.com/path', 'example.com'),
        ]

        for input_domain, expected in test_cases:
            result = CSVIngestor._normalize_domain(input_domain)
            assert result == expected, f"Failed for {input_domain}"


class TestUnstructuredIngestion:
    """Tests for website scraping"""

    @pytest.mark.asyncio
    async def test_scrape_single_website(self):
        """Test scraping a single website"""
        scraper = WebsiteScraper(timeout=5)
        result = await scraper.fetch_website('example.com')

        assert result['domain'] == 'example.com'
        assert result['status'] in ['success', 'failed']

        if result['status'] == 'success':
            assert result['text_snippet'] is not None
            assert len(result['text_snippet']) > 0

    @pytest.mark.asyncio
    async def test_scrape_multiple_websites(self):
        """Test scraping multiple websites concurrently"""
        domains = ['example.com', 'python.org']
        results = await scrape_companies(domains)

        assert len(results) == len(domains)
        assert all('domain' in r for r in results)
        assert all('status' in r for r in results)

    @pytest.mark.asyncio
    async def test_scrape_invalid_domain(self):
        """Test scraping an invalid domain"""
        scraper = WebsiteScraper(timeout=2, max_retries=1)
        result = await scraper.fetch_website('this-domain-definitely-does-not-exist-12345.com')

        assert result['status'] == 'failed'
        assert result['text_snippet'] is None
