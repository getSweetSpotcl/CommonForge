"""
LLM-powered company enrichment using LangChain and OpenAI.

Analyzes company data to generate ICP fit scores, segments, and personalized pitches.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import asyncio
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class CompanyEnrichment(BaseModel):
    """Structured output schema for company enrichment"""

    icp_fit_score: int = Field(
        description="ICP fit score from 0-100. Higher means better fit for B2B SaaS.",
        ge=0,
        le=100
    )

    segment: str = Field(
        description="Company segment: SMB, Mid-Market, or Enterprise",
        pattern="^(SMB|Mid-Market|Enterprise)$"
    )

    primary_use_case: str = Field(
        description="Main use case or pain point this company would have"
    )

    risk_flags: List[str] = Field(
        description="List of risk factors or red flags (empty list if none)"
    )

    personalized_pitch: str = Field(
        description="Personalized sales pitch tailored to this company (2-3 sentences)"
    )


# ICP Scoring Prompt
ENRICHMENT_PROMPT = """You are an expert B2B SaaS sales analyst specializing in lead qualification and ICP (Ideal Customer Profile) scoring.

Your task is to analyze a company and determine:
1. How well they fit the ICP for a B2B SaaS sales engagement tool
2. Their segment classification
3. Their primary use case
4. Any risk flags
5. A personalized sales pitch

## ICP Scoring Criteria (0-100)

Score companies based on these factors:

**High Score Indicators (70-100):**
- B2B SaaS companies with sales teams
- Fast-growing tech companies (50-500 employees)
- Companies in sales-intensive industries (SaaS, MarTech, FinTech)
- Strong online presence and modern tech stack
- Located in US, Canada, UK, or Western Europe
- Clear signs of growth and scaling

**Medium Score Indicators (40-69):**
- B2B companies with moderate sales needs
- Established companies with digital presence
- Companies in adjacent industries (consulting, agencies)
- 20-50 or 500-2000 employees
- International companies with English presence

**Low Score Indicators (0-39):**
- B2C or non-tech companies
- Very small (<20 employees) or very large (>2000 employees)
- Industries with low sales tech adoption
- Poor online presence or outdated practices
- Companies in challenging markets

## Segment Classification

- **SMB:** 1-200 employees, simpler sales process
- **Mid-Market:** 201-2000 employees, established sales teams
- **Enterprise:** 2000+ employees, complex enterprise sales

## Risk Flags

Flag any concerns:
- "Limited online presence" - Minimal website content
- "Unclear value proposition" - Hard to understand what they do
- "Non-tech industry" - Low likelihood of SaaS adoption
- "Geographic challenges" - Difficult market or region
- "Size mismatch" - Too small or too large
- "Competitor" - Appears to be a competitor
- "Budget concerns" - May not have budget for premium tools

## Company Information

**Company Name:** {company_name}
**Domain:** {domain}
**Country:** {country}
**Employee Count:** {employee_count}
**Industry:** {industry_raw}

**Website Content:**
{website_text_snippet}

---

Analyze this company and provide a structured assessment.

{format_instructions}
"""


class LLMEnricher:
    """LLM-powered company enrichment"""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize LLM enricher.

        Args:
            model: OpenAI model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens for response
            rate_limit_delay: Delay between API calls (seconds)
        """
        self.model = model or settings.OPENAI_MODEL
        self.temperature = temperature or settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self.rate_limit_delay = rate_limit_delay

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Initialize parser
        self.parser = PydanticOutputParser(pydantic_object=CompanyEnrichment)

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template(ENRICHMENT_PROMPT)

    async def enrich_company(self, company: Dict) -> Dict:
        """
        Enrich a single company with LLM analysis.

        Args:
            company: Company data dict

        Returns:
            Dict: Enrichment result with all fields

        Raises:
            Exception: If enrichment fails
        """
        logger.info(f"Enriching company: {company['company_name']}")

        try:
            # Prepare input
            input_data = {
                'company_name': company['company_name'],
                'domain': company['domain'],
                'country': company['country'],
                'employee_count': company['employee_count'],
                'industry_raw': company['industry_raw'],
                'website_text_snippet': company['website_text_snippet'] or "No website content available",
                'format_instructions': self.parser.get_format_instructions()
            }

            # Create chain
            chain = self.prompt | self.llm | self.parser

            # Invoke LLM (async)
            result = await chain.ainvoke(input_data)

            logger.info(
                f"✓ Enriched {company['company_name']}: "
                f"Score={result.icp_fit_score}, Segment={result.segment}"
            )

            return result.model_dump()

        except Exception as e:
            logger.error(f"✗ Failed to enrich {company['company_name']}: {e}")
            raise

    async def enrich_companies_batch(
        self,
        companies: List[Dict],
        max_concurrent: int = 3
    ) -> List[Dict]:
        """
        Enrich multiple companies with rate limiting.

        Args:
            companies: List of company dicts
            max_concurrent: Maximum concurrent API calls

        Returns:
            List[Dict]: List of enrichment results (same order as input)
        """
        logger.info(
            f"Starting batch enrichment for {len(companies)} companies "
            f"(max {max_concurrent} concurrent)"
        )

        results = []
        errors = []

        # Process in batches to respect rate limits
        for i in range(0, len(companies), max_concurrent):
            batch = companies[i:i + max_concurrent]
            batch_num = (i // max_concurrent) + 1
            total_batches = (len(companies) + max_concurrent - 1) // max_concurrent

            logger.info(f"Processing batch {batch_num}/{total_batches}...")

            # Create tasks for batch
            tasks = [self.enrich_company(company) for company in batch]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results and errors
            for company, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error enriching {company['company_name']}: {result}")
                    errors.append({
                        'company': company['company_name'],
                        'error': str(result)
                    })
                    # Add failed result
                    results.append({
                        'icp_fit_score': None,
                        'segment': None,
                        'primary_use_case': None,
                        'risk_flags': [],
                        'personalized_pitch': None,
                        'error': str(result)
                    })
                else:
                    results.append(result)

            # Rate limit delay between batches
            if i + max_concurrent < len(companies):
                await asyncio.sleep(self.rate_limit_delay)

        # Log summary
        successful = sum(1 for r in results if r.get('icp_fit_score') is not None)
        failed = len(results) - successful

        logger.info(
            f"Batch enrichment complete: "
            f"{successful} successful, {failed} failed"
        )

        if errors:
            logger.warning(f"Errors encountered: {errors}")

        return results


async def enrich_companies(companies: List[Dict]) -> List[Dict]:
    """
    Convenience function to enrich multiple companies.

    Args:
        companies: List of company dicts (must have website_text_snippet)

    Returns:
        List[Dict]: Enrichment results

    Example:
        >>> from pathlib import Path
        >>> from src.ingestion.structured import load_companies_from_csv
        >>> from src.ingestion.unstructured import scrape_companies
        >>> from src.processing.cleaning import merge_structured_unstructured
        >>>
        >>> # Load and scrape
        >>> csv_data = load_companies_from_csv(Path('data/companies.csv'))
        >>> scraped = await scrape_companies([c['domain'] for c in csv_data])
        >>> merged = merge_structured_unstructured(csv_data, scraped)
        >>>
        >>> # Enrich
        >>> enriched = await enrich_companies(merged)
    """
    enricher = LLMEnricher()
    return await enricher.enrich_companies_batch(companies)


# Test script
if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.ingestion.structured import load_companies_from_csv
    from src.ingestion.unstructured import scrape_companies
    from src.processing.cleaning import merge_structured_unstructured, prepare_for_enrichment

    async def test_enrichment():
        print("=" * 60)
        print("LLM ENRICHMENT TEST")
        print("=" * 60)

        # Load data
        print("\n1. Loading and scraping...")
        csv_path = Path("data/companies.csv")
        structured = load_companies_from_csv(csv_path)
        domains = [c['domain'] for c in structured]
        scraped = await scrape_companies(domains)

        # Merge and prepare
        print("\n2. Merging data...")
        merged = merge_structured_unstructured(structured, scraped)
        ready = prepare_for_enrichment(merged)
        print(f"   ✓ {len(ready)} companies ready for enrichment")

        # Enrich (test with first 2 companies only)
        print("\n3. Enriching companies...")
        test_companies = ready[:2]
        enricher = LLMEnricher()
        results = await enricher.enrich_companies_batch(test_companies)

        # Display results
        print("\n4. Enrichment Results:")
        print("=" * 60)

        for company, enrichment in zip(test_companies, results):
            print(f"\n**{company['company_name']}** ({company['domain']})")
            print(f"ICP Fit Score: {enrichment.get('icp_fit_score', 'N/A')}/100")
            print(f"Segment: {enrichment.get('segment', 'N/A')}")
            print(f"Use Case: {enrichment.get('primary_use_case', 'N/A')}")
            print(f"Risk Flags: {enrichment.get('risk_flags', [])}")
            print(f"\nPitch: {enrichment.get('personalized_pitch', 'N/A')}")
            print("-" * 60)

        print("\n✅ LLM ENRICHMENT TEST COMPLETE")
        print("=" * 60)

    asyncio.run(test_enrichment())
