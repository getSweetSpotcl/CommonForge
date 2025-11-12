"""
Unstructured data ingestion via web scraping.

Fetches company websites and extracts text content asynchronously.
"""

import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, List
import logging

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


# Test script
if __name__ == "__main__":
    import asyncio

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
