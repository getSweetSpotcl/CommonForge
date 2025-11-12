# Phase 4: LLM Processing & Enrichment

**Duration:** 4-5 hours
**Priority:** Critical - Core AI functionality
**Dependencies:** Phase 1, 2, 3 (all previous phases)

---

## Objectives

1. Design ICP scoring prompt for LLM
2. Implement LangChain enrichment chain
3. Create data cleaning and merging utilities
4. Add async processing with rate limiting
5. Implement structured JSON output parsing
6. Add error handling and validation
7. Test with real company data

---

## Task Checklist

### 4.1 Implement Data Cleaning (`src/processing/cleaning.py`)

**Purpose:** Merge structured and unstructured data for enrichment

**Implementation:**

```python
"""
Data cleaning and preparation for LLM enrichment.

Merges structured company data with scraped website content.
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def merge_structured_unstructured(
    structured_data: List[Dict],
    scraped_data: List[Dict]
) -> List[Dict]:
    """
    Merge structured company data with scraped website content.

    Args:
        structured_data: List of company dicts from CSV
        scraped_data: List of scraping result dicts

    Returns:
        List[Dict]: Merged company records ready for enrichment

    Example:
        >>> structured = [{'company_name': 'Acme', 'domain': 'acme.com', ...}]
        >>> scraped = [{'domain': 'acme.com', 'text_snippet': '...', 'status': 'success'}]
        >>> merged = merge_structured_unstructured(structured, scraped)
    """
    # Create lookup dictionary for O(1) access
    scraped_lookup = {item['domain']: item for item in scraped_data}

    merged_companies = []

    for company in structured_data:
        domain = company['domain']
        scraped = scraped_lookup.get(domain, {})

        # Merge data
        merged = {
            # Structured data
            'company_name': company['company_name'],
            'domain': company['domain'],
            'country': company['country'],
            'employee_count': company['employee_count'],
            'industry_raw': company['industry_raw'],

            # Unstructured data
            'website_text_snippet': scraped.get('text_snippet'),
            'scraping_status': scraped.get('status', 'failed'),
            'scraping_error': scraped.get('error'),

            # Enrichment status (to be populated later)
            'enrichment_status': 'pending',
            'enrichment_error': None,
        }

        merged_companies.append(merged)

    logger.info(f"Merged {len(merged_companies)} company records")

    return merged_companies


def prepare_for_enrichment(merged_data: List[Dict]) -> List[Dict]:
    """
    Filter and prepare companies for LLM enrichment.

    Only includes companies with successfully scraped website data.
    Companies without website data will be skipped for enrichment.

    Args:
        merged_data: List of merged company records

    Returns:
        List[Dict]: Companies ready for enrichment
    """
    ready_for_enrichment = [
        company for company in merged_data
        if company['scraping_status'] == 'success'
        and company['website_text_snippet']
    ]

    skipped = len(merged_data) - len(ready_for_enrichment)

    logger.info(
        f"Prepared {len(ready_for_enrichment)} companies for enrichment "
        f"({skipped} skipped due to scraping failures)"
    )

    return ready_for_enrichment
```

---

### 4.2 Implement LLM Enrichment Chain (`src/processing/llm_chain.py`)

**Purpose:** LangChain-based LLM enrichment pipeline

**Implementation:**

```python
"""
LLM enrichment chain using LangChain and OpenAI.

Analyzes companies and generates ICP fit scores, segments, and insights.
"""

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import asyncio
import logging

from src.config import settings

logger = logging.getLogger(__name__)


# Define output schema using Pydantic
class CompanyEnrichment(BaseModel):
    """Schema for LLM enrichment output"""

    icp_fit_score: int = Field(
        description="ICP fit score from 0-100, where 100 is perfect fit",
        ge=0,
        le=100
    )

    segment: str = Field(
        description="Company segment based on size and characteristics",
        pattern="^(SMB|Mid-Market|Enterprise)$"
    )

    primary_use_case: str = Field(
        description="Primary use case for AI automation platform (1-2 sentences)",
        min_length=10,
        max_length=500
    )

    risk_flags: List[str] = Field(
        description="List of potential risks or concerns (0-5 items)",
        max_items=5
    )

    personalized_pitch: str = Field(
        description="One-sentence personalized sales pitch",
        min_length=20,
        max_length=300
    )


# Create output parser
output_parser = PydanticOutputParser(pydantic_object=CompanyEnrichment)


# Define prompt template
ENRICHMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert B2B sales analyst specializing in AI automation platforms.

Your task is to analyze companies and determine how well they fit the Ideal Customer Profile (ICP) for an AI automation platform that helps businesses:
- Automate repetitive workflows and processes
- Integrate disparate systems and data sources
- Enhance data-driven decision making with AI
- Improve operational efficiency and reduce manual work
- Scale operations without proportional headcount increases

**Scoring Guidelines (0-100):**
- **90-100:** Perfect fit - Clear automation needs, budget, and technical capability
- **70-89:** Strong fit - Good alignment with 1-2 minor concerns
- **50-69:** Moderate fit - Some alignment but notable gaps or risks
- **30-49:** Weak fit - Limited alignment or significant barriers
- **0-29:** Poor fit - Minimal to no alignment with ICP

**Segment Classification:**
- **SMB:** <200 employees, simpler needs, limited budget
- **Mid-Market:** 200-2000 employees, growing operations, moderate complexity
- **Enterprise:** 2000+ employees, complex needs, large budget

{format_instructions}

Provide your analysis in valid JSON format only."""),

    ("human", """Analyze this company:

**Company Profile:**
- Name: {company_name}
- Domain: {domain}
- Country: {country}
- Employee Count: {employee_count:,}
- Industry: {industry_raw}

**Website Content:**
{website_text}

Provide a thorough ICP fit analysis following the specified JSON format.""")
])


class LLMEnricher:
    """Handles LLM-based company enrichment"""

    def __init__(self):
        """Initialize LLM enricher with OpenAI"""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY,
        )

        # Create enrichment chain
        self.chain = ENRICHMENT_PROMPT | self.llm | output_parser

        logger.info(f"Initialized LLM enricher with model: {settings.OPENAI_MODEL}")

    async def enrich_company(self, company_data: Dict) -> Dict:
        """
        Enrich a single company using LLM.

        Args:
            company_data: Company dict with structured and unstructured data

        Returns:
            Dict: Company data with enrichment results
        """
        domain = company_data.get('domain', 'unknown')

        try:
            logger.info(f"Enriching company: {domain}")

            # Prepare input
            website_text = company_data.get('website_text_snippet')

            if not website_text:
                website_text = "No website content available"

            # Invoke LLM chain
            result = await self.chain.ainvoke({
                'company_name': company_data['company_name'],
                'domain': company_data['domain'],
                'country': company_data['country'],
                'employee_count': company_data['employee_count'],
                'industry_raw': company_data['industry_raw'],
                'website_text': website_text,
                'format_instructions': output_parser.get_format_instructions()
            })

            # Convert Pydantic model to dict
            enrichment = result.dict()

            # Merge with original data
            enriched_company = {
                **company_data,
                'icp_fit_score': enrichment['icp_fit_score'],
                'segment': enrichment['segment'],
                'primary_use_case': enrichment['primary_use_case'],
                'risk_flags': enrichment['risk_flags'],
                'personalized_pitch': enrichment['personalized_pitch'],
                'enrichment_status': 'success',
                'enrichment_error': None,
            }

            logger.info(
                f"✓ Enriched {domain} - "
                f"Score: {enrichment['icp_fit_score']}, "
                f"Segment: {enrichment['segment']}"
            )

            return enriched_company

        except Exception as e:
            logger.error(f"✗ Failed to enrich {domain}: {e}")

            return {
                **company_data,
                'icp_fit_score': None,
                'segment': None,
                'primary_use_case': None,
                'risk_flags': None,
                'personalized_pitch': None,
                'enrichment_status': 'failed',
                'enrichment_error': str(e),
            }

    async def enrich_companies_batch(
        self,
        companies: List[Dict],
        concurrency: int = None
    ) -> List[Dict]:
        """
        Enrich multiple companies with rate limiting.

        Args:
            companies: List of company dicts
            concurrency: Max concurrent LLM calls (default from settings)

        Returns:
            List[Dict]: Enriched company records
        """
        concurrency = concurrency or settings.CONCURRENT_LLM_CALLS

        logger.info(
            f"Starting batch enrichment of {len(companies)} companies "
            f"with concurrency={concurrency}"
        )

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(concurrency)

        async def enrich_with_semaphore(company):
            async with semaphore:
                return await self.enrich_company(company)

        # Process all companies
        tasks = [enrich_with_semaphore(company) for company in companies]
        enriched = await asyncio.gather(*tasks)

        # Log summary
        successful = sum(
            1 for c in enriched
            if c.get('enrichment_status') == 'success'
        )
        failed = len(enriched) - successful

        logger.info(
            f"Batch enrichment complete: "
            f"{successful} successful, {failed} failed"
        )

        return enriched


async def enrich_companies(companies: List[Dict]) -> List[Dict]:
    """
    Convenience function to enrich multiple companies.

    Args:
        companies: List of company dicts (must include website_text_snippet)

    Returns:
        List[Dict]: Enriched companies

    Example:
        >>> import asyncio
        >>> companies = [{'company_name': 'Acme', ...}]
        >>> enriched = asyncio.run(enrich_companies(companies))
    """
    enricher = LLMEnricher()
    return await enricher.enrich_companies_batch(companies)
```

---

### 4.3 Create Test Scripts

**File:** `tests/test_processing.py`

```python
"""
Tests for LLM processing and enrichment.
"""

import pytest
import asyncio
from src.processing.cleaning import (
    merge_structured_unstructured,
    prepare_for_enrichment
)
from src.processing.llm_chain import enrich_companies, LLMEnricher


class TestDataCleaning:
    """Tests for data cleaning utilities"""

    def test_merge_structured_unstructured(self):
        """Test merging structured and unstructured data"""
        structured = [
            {
                'company_name': 'Test Corp',
                'domain': 'test.com',
                'country': 'USA',
                'employee_count': 100,
                'industry_raw': 'Technology'
            }
        ]

        scraped = [
            {
                'domain': 'test.com',
                'text_snippet': 'We are a technology company...',
                'status': 'success',
                'error': None
            }
        ]

        merged = merge_structured_unstructured(structured, scraped)

        assert len(merged) == 1
        assert merged[0]['company_name'] == 'Test Corp'
        assert merged[0]['website_text_snippet'] == 'We are a technology company...'
        assert merged[0]['scraping_status'] == 'success'

    def test_prepare_for_enrichment(self):
        """Test filtering companies ready for enrichment"""
        merged_data = [
            {
                'domain': 'success.com',
                'scraping_status': 'success',
                'website_text_snippet': 'Content here',
            },
            {
                'domain': 'failed.com',
                'scraping_status': 'failed',
                'website_text_snippet': None,
            },
        ]

        ready = prepare_for_enrichment(merged_data)

        assert len(ready) == 1
        assert ready[0]['domain'] == 'success.com'


class TestLLMEnrichment:
    """Tests for LLM enrichment (requires API key)"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_enrich_single_company(self):
        """Test enriching a single company"""
        company = {
            'company_name': 'HubSpot',
            'domain': 'hubspot.com',
            'country': 'USA',
            'employee_count': 7400,
            'industry_raw': 'Marketing & CRM Software',
            'website_text_snippet': 'HubSpot provides marketing, sales, and service software...',
            'scraping_status': 'success',
        }

        enricher = LLMEnricher()
        result = await enricher.enrich_company(company)

        assert result['enrichment_status'] == 'success'
        assert result['icp_fit_score'] is not None
        assert 0 <= result['icp_fit_score'] <= 100
        assert result['segment'] in ['SMB', 'Mid-Market', 'Enterprise']
        assert len(result['primary_use_case']) > 0
        assert isinstance(result['risk_flags'], list)
        assert len(result['personalized_pitch']) > 0
```

---

### 4.4 Create Manual Testing Script

**File:** `tests/test_enrichment_manual.py`

```python
"""
Manual test for LLM enrichment with sample data.

Run this to test the complete enrichment pipeline end-to-end.
"""

import asyncio
from pathlib import Path
from src.ingestion.structured import load_companies_from_csv
from src.ingestion.unstructured import scrape_companies
from src.processing.cleaning import (
    merge_structured_unstructured,
    prepare_for_enrichment
)
from src.processing.llm_chain import enrich_companies


async def main():
    """Test complete enrichment pipeline"""

    print("=" * 70)
    print("MANUAL LLM ENRICHMENT TEST")
    print("=" * 70)

    # Step 1: Load CSV
    print("\n[1/5] Loading companies from CSV...")
    csv_path = Path("data/companies.csv")
    companies = load_companies_from_csv(csv_path)
    print(f"      ✓ Loaded {len(companies)} companies")

    # Step 2: Scrape websites
    print("\n[2/5] Scraping company websites...")
    domains = [c['domain'] for c in companies]
    scraped = await scrape_companies(domains)
    successful = sum(1 for s in scraped if s['status'] == 'success')
    print(f"      ✓ Scraped {successful}/{len(domains)} websites")

    # Step 3: Merge data
    print("\n[3/5] Merging structured and unstructured data...")
    merged = merge_structured_unstructured(companies, scraped)
    print(f"      ✓ Merged {len(merged)} records")

    # Step 4: Prepare for enrichment
    print("\n[4/5] Preparing for enrichment...")
    ready = prepare_for_enrichment(merged)
    print(f"      ✓ {len(ready)} companies ready for enrichment")

    # Step 5: Enrich with LLM
    print("\n[5/5] Enriching with LLM (this may take a while)...")
    enriched = await enrich_companies(ready[:2])  # Test with first 2 only
    successful_enrichment = sum(
        1 for e in enriched
        if e.get('enrichment_status') == 'success'
    )
    print(f"      ✓ Enriched {successful_enrichment}/{len(enriched)} companies")

    # Display results
    print("\n" + "=" * 70)
    print("ENRICHMENT RESULTS")
    print("=" * 70)

    for company in enriched:
        print(f"\n{'='*70}")
        print(f"Company: {company['company_name']}")
        print(f"Domain: {company['domain']}")
        print(f"Employees: {company['employee_count']:,}")
        print(f"Country: {company['country']}")
        print(f"-" * 70)

        if company['enrichment_status'] == 'success':
            print(f"ICP Fit Score: {company['icp_fit_score']}/100")
            print(f"Segment: {company['segment']}")
            print(f"\nPrimary Use Case:")
            print(f"  {company['primary_use_case']}")
            print(f"\nRisk Flags:")
            for flag in company['risk_flags']:
                print(f"  - {flag}")
            print(f"\nPersonalized Pitch:")
            print(f"  {company['personalized_pitch']}")
        else:
            print(f"❌ Enrichment failed: {company['enrichment_error']}")

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
```

**Run test:**
```bash
python tests/test_enrichment_manual.py
```

---

## Verification Steps

### 4.5 Test Data Cleaning

```bash
# Test merging utilities
pytest tests/test_processing.py::TestDataCleaning -v
```

### 4.6 Test LLM Enrichment

```bash
# Run manual enrichment test (requires OpenAI API key)
python tests/test_enrichment_manual.py

# Expected: Successfully enriched companies with scores and insights
```

### 4.7 Verify Output Quality

Check that enriched companies have:
- ✅ ICP score between 0-100
- ✅ Valid segment (SMB/Mid-Market/Enterprise)
- ✅ Meaningful use case description
- ✅ Relevant risk flags
- ✅ Personalized pitch

---

## Prompt Engineering Tips

### Improving Prompt Quality

1. **Be specific about scoring criteria**
2. **Provide examples of good vs bad fits**
3. **Request structured output explicitly**
4. **Include domain knowledge in system prompt**
5. **Test with diverse company types**

### Adjusting Temperature

- **Lower (0.1-0.3):** More deterministic, consistent
- **Medium (0.4-0.7):** Balanced creativity
- **Higher (0.8-1.0):** More creative, less consistent

---

## Common Issues & Solutions

### Issue 1: JSON Parsing Errors

**Error:** `OutputParserException: Failed to parse`

**Solution:**
- Ensure Pydantic schema is valid
- Add retry logic for failed parses
- Log raw LLM output for debugging

### Issue 2: Rate Limit Errors

**Error:** `RateLimitError: Rate limit exceeded`

**Solution:**
- Reduce `CONCURRENT_LLM_CALLS` in `.env`
- Add exponential backoff retry logic
- Use lower-tier model for testing

### Issue 3: Inconsistent Scores

**Problem:** Scores vary widely for similar companies

**Solution:**
- Lower temperature setting
- Add more specific scoring guidelines
- Include examples in prompt
- Use few-shot prompting

---

## Success Criteria

After completing Phase 4, you should have:

- ✅ Data cleaning utilities working
- ✅ LangChain enrichment chain configured
- ✅ Structured JSON output parsing
- ✅ Rate-limited async processing
- ✅ Successful enrichment of sample companies
- ✅ High-quality, consistent LLM outputs

---

## Next Steps

Once Phase 4 is complete:
1. Verify enrichment quality
2. Tune prompt for better results
3. Proceed to **Phase 5: API Serving Layer**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Implement cleaning.py | 30 min |
| Implement llm_chain.py | 90 min |
| Prompt engineering | 60 min |
| Create tests | 45 min |
| Manual testing & tuning | 45 min |
| **Total** | **4.5 hours** |
