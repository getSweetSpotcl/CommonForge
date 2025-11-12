# Phase 3: Data Ingestion Layer

**Duration:** 3-4 hours
**Priority:** High - Core pipeline functionality
**Dependencies:** Phase 1 (Setup), Phase 2 (Data Layer)

---

## Objectives

1. Implement CSV structured data ingestion
2. Build async website scraper
3. Create HTML parsing and text extraction utilities
4. Implement error handling and retry logic
5. Add domain normalization and validation
6. Test with sample data

---

## Task Checklist

### 3.1 Implement Structured Data Ingestion (`src/ingestion/structured.py`)

**Purpose:** Load and validate company data from CSV files

**Implementation:**

```python
"""
Structured data ingestion from CSV files.

Handles loading, validation, and normalization of company data.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class CSVIngestor:
    """Handles CSV file ingestion and validation"""

    REQUIRED_COLUMNS = [
        'company_name',
        'domain',
        'country',
        'employee_count',
        'industry_raw'
    ]

    def __init__(self, csv_path: Path):
        """
        Initialize CSV ingestor.

        Args:
            csv_path: Path to CSV file
        """
        self.csv_path = Path(csv_path)

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        if not self.csv_path.suffix.lower() == '.csv':
            raise ValueError(f"File must be a CSV: {csv_path}")

    def load(self) -> pd.DataFrame:
        """
        Load and validate CSV file.

        Returns:
            pd.DataFrame: Validated dataframe

        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        logger.info(f"Loading CSV from {self.csv_path}")

        try:
            df = pd.read_csv(self.csv_path)
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            raise ValueError(f"Failed to read CSV: {e}")

        # Validate columns
        self._validate_columns(df)

        # Clean and normalize data
        df = self._clean_data(df)

        logger.info(f"Loaded {len(df)} companies from CSV")
        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that all required columns are present.

        Args:
            df: DataFrame to validate

        Raises:
            ValueError: If required columns are missing
        """
        missing_columns = set(self.REQUIRED_COLUMNS) - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}\n"
                f"Required columns: {self.REQUIRED_COLUMNS}"
            )

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize company data.

        Args:
            df: Raw dataframe

        Returns:
            pd.DataFrame: Cleaned dataframe
        """
        df = df.copy()

        # Remove rows with missing required fields
        df = df.dropna(subset=self.REQUIRED_COLUMNS)

        # Normalize domain
        df['domain'] = df['domain'].apply(self._normalize_domain)

        # Clean company name
        df['company_name'] = df['company_name'].str.strip()

        # Clean country
        df['country'] = df['country'].str.strip()

        # Ensure employee_count is integer
        df['employee_count'] = pd.to_numeric(
            df['employee_count'],
            errors='coerce'
        )
        df = df.dropna(subset=['employee_count'])
        df['employee_count'] = df['employee_count'].astype(int)

        # Remove duplicates by domain (keep first occurrence)
        df = df.drop_duplicates(subset=['domain'], keep='first')

        # Remove invalid entries
        df = df[df['employee_count'] > 0]
        df = df[df['domain'].str.len() > 0]

        return df

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        """
        Normalize domain to consistent format.

        Args:
            domain: Raw domain string

        Returns:
            str: Normalized domain (lowercase, no protocol, no www)

        Examples:
            'HTTP://WWW.EXAMPLE.COM' -> 'example.com'
            'https://example.com/' -> 'example.com'
            'www.example.com' -> 'example.com'
        """
        if pd.isna(domain):
            return ""

        domain = str(domain).strip().lower()

        # Remove protocol
        domain = domain.replace('http://', '').replace('https://', '')

        # Remove www
        domain = domain.replace('www.', '')

        # Remove trailing slash
        domain = domain.rstrip('/')

        # Remove path (keep only domain)
        domain = domain.split('/')[0]

        # Remove port if present
        domain = domain.split(':')[0]

        return domain

    def to_dicts(self, df: pd.DataFrame) -> List[Dict]:
        """
        Convert DataFrame to list of dictionaries.

        Args:
            df: DataFrame to convert

        Returns:
            List[Dict]: List of company records
        """
        return df.to_dict('records')


def load_companies_from_csv(csv_path: Path) -> List[Dict]:
    """
    Convenience function to load companies from CSV.

    Args:
        csv_path: Path to CSV file

    Returns:
        List[Dict]: List of company records

    Example:
        >>> companies = load_companies_from_csv(Path('data/companies.csv'))
        >>> print(f"Loaded {len(companies)} companies")
    """
    ingestor = CSVIngestor(csv_path)
    df = ingestor.load()
    return ingestor.to_dicts(df)
```

**Test Script:**

```python
if __name__ == "__main__":
    from pathlib import Path
    from src.ingestion.structured import load_companies_from_csv

    # Test with sample data
    csv_path = Path("data/companies.csv")

    print(f"Loading companies from {csv_path}...")
    companies = load_companies_from_csv(csv_path)

    print(f"\n✓ Loaded {len(companies)} companies\n")

    for i, company in enumerate(companies, 1):
        print(f"{i}. {company['company_name']}")
        print(f"   Domain: {company['domain']}")
        print(f"   Country: {company['country']}")
        print(f"   Employees: {company['employee_count']:,}")
        print(f"   Industry: {company['industry_raw']}")
        print()
```

**Run test:**
```bash
python -m src.ingestion.structured
```

---

### 3.2 Implement Website Scraper (`src/ingestion/unstructured.py`)

**Purpose:** Scrape company websites and extract text content

**Implementation:**

```python
"""
Unstructured data ingestion via web scraping.

Fetches company websites and extracts text content asynchronously.
"""

import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, List, Optional
import logging
from urllib.parse import urljoin

from src.config import settings

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """Asynchronous website scraper using HTTPX"""

    def __init__(
        self,
        timeout: int = None,
        max_retries: int = None,
        user_agent: str = None,
    ):
        """
        Initialize website scraper.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            user_agent: User-Agent header for requests
        """
        self.timeout = timeout or settings.SCRAPER_TIMEOUT
        self.max_retries = max_retries or settings.SCRAPER_MAX_RETRIES
        self.user_agent = user_agent or settings.SCRAPER_USER_AGENT

    async def fetch_website(self, domain: str) -> Dict:
        """
        Fetch and parse a single website.

        Args:
            domain: Domain to fetch (e.g., 'example.com')

        Returns:
            Dict with keys:
                - domain: str
                - text_snippet: Optional[str]
                - status: 'success' | 'failed'
                - error: Optional[str]
                - url: str (actual URL fetched)
        """
        # Try HTTPS first, fallback to HTTP
        urls = [f"https://{domain}", f"http://{domain}"]

        for attempt in range(self.max_retries):
            for url in urls:
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout,
                        follow_redirects=True,
                    ) as client:
                        logger.debug(f"Fetching {url} (attempt {attempt + 1})")

                        response = await client.get(
                            url,
                            headers={'User-Agent': self.user_agent}
                        )

                        response.raise_for_status()

                        # Parse HTML and extract text
                        text_snippet = self._extract_text(response.text)

                        logger.info(f"✓ Successfully scraped {domain}")

                        return {
                            'domain': domain,
                            'text_snippet': text_snippet,
                            'status': 'success',
                            'error': None,
                            'url': str(response.url),
                        }

                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error for {url}: {e.response.status_code}")
                    continue

                except httpx.TimeoutException:
                    logger.warning(f"Timeout for {url}")
                    continue

                except Exception as e:
                    logger.warning(f"Error fetching {url}: {e}")
                    continue

            # Exponential backoff between retries
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        # All attempts failed
        logger.error(f"✗ Failed to scrape {domain} after {self.max_retries} attempts")

        return {
            'domain': domain,
            'text_snippet': None,
            'status': 'failed',
            'error': 'Failed to fetch after multiple attempts',
            'url': None,
        }

    def _extract_text(self, html: str) -> str:
        """
        Extract main text content from HTML.

        Args:
            html: Raw HTML string

        Returns:
            str: Extracted and cleaned text
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # Get text from main content areas (prioritize main, article, section)
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=['content', 'main-content']) or
            soup.body or
            soup
        )

        # Extract text
        text = main_content.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = ' '.join(text.split())

        # Truncate to maximum length
        max_length = settings.MAX_WEBSITE_TEXT_LENGTH
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + "..."

        return text

    async def fetch_multiple(self, domains: List[str]) -> List[Dict]:
        """
        Fetch multiple websites concurrently.

        Args:
            domains: List of domains to fetch

        Returns:
            List[Dict]: List of scraping results
        """
        logger.info(f"Starting scrape for {len(domains)} domains...")

        tasks = [self.fetch_website(domain) for domain in domains]
        results = await asyncio.gather(*tasks)

        # Log summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful

        logger.info(
            f"Scraping complete: {successful} successful, {failed} failed"
        )

        return results


async def scrape_companies(domains: List[str]) -> List[Dict]:
    """
    Convenience function to scrape multiple companies.

    Args:
        domains: List of domain names

    Returns:
        List[Dict]: Scraping results

    Example:
        >>> import asyncio
        >>> domains = ['example.com', 'test.com']
        >>> results = asyncio.run(scrape_companies(domains))
    """
    scraper = WebsiteScraper()
    return await scraper.fetch_multiple(domains)
```

**Test Script:**

```python
if __name__ == "__main__":
    import asyncio
    from src.ingestion.unstructured import scrape_companies

    # Test domains
    test_domains = [
        'hubspot.com',
        'asana.com',
        'monday.com',
    ]

    print(f"Testing scraper with {len(test_domains)} domains...\n")

    async def main():
        results = await scrape_companies(test_domains)

        for result in results:
            print(f"Domain: {result['domain']}")
            print(f"Status: {result['status']}")

            if result['status'] == 'success':
                snippet = result['text_snippet'][:200]
                print(f"Text: {snippet}...")
            else:
                print(f"Error: {result['error']}")

            print()

    asyncio.run(main())
```

**Run test:**
```bash
python -m src.ingestion.unstructured
```

---

### 3.3 Create Combined Ingestion Test

**File:** `tests/test_ingestion.py`

```python
"""
Tests for data ingestion layer.
"""

import pytest
import asyncio
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
```

**Run tests:**
```bash
pytest tests/test_ingestion.py -v
```

---

### 3.4 Create End-to-End Ingestion Test

**File:** `tests/test_full_ingestion.py`

```python
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
    domains = [c['domain'] for c in companies]
    scraped_data = await scrape_companies(domains)

    successful_scrapes = sum(1 for s in scraped_data if s['status'] == 'success')
    print(f"   ✓ Scraped {successful_scrapes}/{len(domains)} websites successfully")

    # Step 3: Merge data
    print("\n3. Merging structured and unstructured data...")
    scraped_lookup = {s['domain']: s for s in scraped_data}

    enriched_companies = []
    for company in companies:
        scraped = scraped_lookup.get(company['domain'], {})

        enriched = {
            **company,
            'website_text_snippet': scraped.get('text_snippet'),
            'scraping_status': scraped.get('status', 'failed'),
            'scraping_error': scraped.get('error'),
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

        if company['website_text_snippet']:
            snippet = company['website_text_snippet'][:150]
            print(f"Text: {snippet}...")

    print("\n" + "=" * 60)
    print("✅ FULL INGESTION TEST COMPLETE")
    print("=" * 60)

    return enriched_companies


if __name__ == "__main__":
    asyncio.run(test_full_ingestion())
```

**Run test:**
```bash
python tests/test_full_ingestion.py
```

---

## Verification Steps

### 3.5 Verify Structured Ingestion

```bash
# Test CSV loading
python -m src.ingestion.structured

# Expected output:
# Loading companies from data/companies.csv...
# ✓ Loaded 5 companies
# [List of companies with details]
```

### 3.6 Verify Web Scraping

```bash
# Test web scraping
python -m src.ingestion.unstructured

# Expected output:
# Testing scraper with 3 domains...
# ✓ Successfully scraped [domain]
# [Scraped content previews]
```

### 3.7 Run Full Ingestion Test

```bash
# Test complete ingestion pipeline
python tests/test_full_ingestion.py

# Should complete successfully with merged data
```

### 3.8 Run Unit Tests

```bash
# Run all ingestion tests
pytest tests/test_ingestion.py -v

# Expected: All tests pass
```

---

## Common Issues & Solutions

### Issue 1: SSL Certificate Errors

**Error:** `ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`

**Solution:**
```python
# In unstructured.py, modify AsyncClient:
async with httpx.AsyncClient(
    timeout=self.timeout,
    follow_redirects=True,
    verify=False,  # Disable SSL verification (dev only!)
) as client:
```

### Issue 2: Timeout Errors

**Error:** `httpx.TimeoutException`

**Solution:**
- Increase timeout in `.env`: `SCRAPER_TIMEOUT=30`
- Or reduce concurrency if network is slow

### Issue 3: Rate Limiting

**Error:** HTTP 429 Too Many Requests

**Solution:**
```python
# Add delay between requests
await asyncio.sleep(1)  # 1 second delay
```

---

## Success Criteria

After completing Phase 3, you should have:

- ✅ Working CSV ingestion with validation
- ✅ Async website scraper with error handling
- ✅ Domain normalization utilities
- ✅ Text extraction from HTML
- ✅ Successful test of full ingestion pipeline
- ✅ All unit tests passing

---

## Next Steps

Once Phase 3 is complete:
1. Verify ingestion works with sample data
2. Check scraped text quality
3. Proceed to **Phase 4: LLM Processing & Enrichment**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Implement structured.py | 45 min |
| Implement unstructured.py | 60 min |
| Create unit tests | 30 min |
| Create integration test | 30 min |
| Testing and debugging | 45 min |
| **Total** | **3.5 hours** |
