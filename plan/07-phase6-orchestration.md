# Phase 6: Pipeline Orchestration

**Duration:** 2-3 hours
**Priority:** High - Ties all components together
**Dependencies:** All previous phases (1-5)

---

## Objectives

1. Create main pipeline orchestration script
2. Implement CLI argument parsing
3. Add progress tracking and logging
4. Implement database operations (init, reset, upsert)
5. Create helper scripts for common operations
6. Add comprehensive error handling
7. Test end-to-end pipeline

---

## Task Checklist

### 6.1 Implement Main Pipeline (`src/pipeline.py`)

**Purpose:** Orchestrate the complete enrichment workflow

**Implementation:**

```python
"""
Main pipeline orchestration for CommonForge.

Coordinates the end-to-end enrichment workflow:
1. Load structured data from CSV
2. Scrape company websites
3. Merge data
4. Enrich with LLM
5. Persist to database
"""

import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Dict
import sys

from src.config import settings
from src.db import (
    init_db,
    drop_all_tables,
    check_connection,
    SessionLocal,
)
from src.models import Company
from src.ingestion.structured import load_companies_from_csv
from src.ingestion.unstructured import scrape_companies
from src.processing.cleaning import (
    merge_structured_unstructured,
    prepare_for_enrichment,
)
from src.processing.llm_chain import enrich_companies

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


class Pipeline:
    """Main enrichment pipeline orchestrator"""

    def __init__(self, csv_path: Path, dry_run: bool = False):
        """
        Initialize pipeline.

        Args:
            csv_path: Path to companies CSV file
            dry_run: If True, don't write to database
        """
        self.csv_path = csv_path
        self.dry_run = dry_run
        self.stats = {
            'csv_loaded': 0,
            'scraped_success': 0,
            'scraped_failed': 0,
            'enriched_success': 0,
            'enriched_failed': 0,
            'persisted': 0,
        }

    async def run(self) -> Dict:
        """
        Run the complete enrichment pipeline.

        Returns:
            Dict: Pipeline statistics
        """
        logger.info("=" * 70)
        logger.info("STARTING COMMONFORGE ENRICHMENT PIPELINE")
        logger.info("=" * 70)

        try:
            # Step 1: Load CSV
            logger.info("\n[1/5] Loading companies from CSV...")
            companies = self._load_csv()
            self.stats['csv_loaded'] = len(companies)
            logger.info(f"      ✓ Loaded {len(companies)} companies")

            # Step 2: Scrape websites
            logger.info("\n[2/5] Scraping company websites...")
            scraped = await self._scrape_websites(companies)
            self.stats['scraped_success'] = sum(
                1 for s in scraped if s['status'] == 'success'
            )
            self.stats['scraped_failed'] = len(scraped) - self.stats['scraped_success']
            logger.info(
                f"      ✓ Scraped {self.stats['scraped_success']}/{len(scraped)} "
                f"websites successfully"
            )

            # Step 3: Merge data
            logger.info("\n[3/5] Merging structured and unstructured data...")
            merged = self._merge_data(companies, scraped)
            logger.info(f"      ✓ Merged {len(merged)} records")

            # Step 4: Prepare and enrich
            logger.info("\n[4/5] Enriching companies with LLM...")
            ready = prepare_for_enrichment(merged)
            logger.info(f"      → {len(ready)} companies ready for enrichment")

            if ready:
                enriched = await self._enrich_companies(ready)
                self.stats['enriched_success'] = sum(
                    1 for e in enriched
                    if e.get('enrichment_status') == 'success'
                )
                self.stats['enriched_failed'] = len(enriched) - self.stats['enriched_success']
                logger.info(
                    f"      ✓ Enriched {self.stats['enriched_success']}/{len(enriched)} "
                    f"companies successfully"
                )

                # Merge back with non-ready companies
                enriched_lookup = {e['domain']: e for e in enriched}
                final_data = []
                for company in merged:
                    if company['domain'] in enriched_lookup:
                        final_data.append(enriched_lookup[company['domain']])
                    else:
                        final_data.append(company)
            else:
                logger.warning("      ⚠ No companies ready for enrichment")
                final_data = merged

            # Step 5: Persist to database
            if not self.dry_run:
                logger.info("\n[5/5] Persisting data to database...")
                persisted = self._persist_to_db(final_data)
                self.stats['persisted'] = persisted
                logger.info(f"      ✓ Persisted {persisted} companies to database")
            else:
                logger.info("\n[5/5] Skipping database persistence (dry run)")

            # Print summary
            self._print_summary()

            return self.stats

        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}", exc_info=True)
            raise

    def _load_csv(self) -> List[Dict]:
        """Load companies from CSV"""
        return load_companies_from_csv(self.csv_path)

    async def _scrape_websites(self, companies: List[Dict]) -> List[Dict]:
        """Scrape company websites"""
        domains = [c['domain'] for c in companies]
        return await scrape_companies(domains)

    def _merge_data(
        self,
        companies: List[Dict],
        scraped: List[Dict]
    ) -> List[Dict]:
        """Merge structured and unstructured data"""
        return merge_structured_unstructured(companies, scraped)

    async def _enrich_companies(self, companies: List[Dict]) -> List[Dict]:
        """Enrich companies with LLM"""
        return await enrich_companies(companies)

    def _persist_to_db(self, companies: List[Dict]) -> int:
        """
        Persist companies to database.

        Uses upsert logic: update if domain exists, insert otherwise.

        Returns:
            int: Number of companies persisted
        """
        db = SessionLocal()
        persisted_count = 0

        try:
            for company_data in companies:
                try:
                    # Check if company exists
                    existing = db.query(Company).filter_by(
                        domain=company_data['domain']
                    ).first()

                    if existing:
                        # Update existing
                        for key, value in company_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        logger.debug(f"Updated company: {company_data['domain']}")
                    else:
                        # Insert new
                        company = Company(**company_data)
                        db.add(company)
                        logger.debug(f"Inserted company: {company_data['domain']}")

                    db.commit()
                    persisted_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to persist {company_data.get('domain')}: {e}"
                    )
                    db.rollback()

            return persisted_count

        finally:
            db.close()

    def _print_summary(self):
        """Print pipeline execution summary"""
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Companies loaded:        {self.stats['csv_loaded']}")
        logger.info(f"Websites scraped:        {self.stats['scraped_success']}")
        logger.info(f"Scraping failures:       {self.stats['scraped_failed']}")
        logger.info(f"Companies enriched:      {self.stats['enriched_success']}")
        logger.info(f"Enrichment failures:     {self.stats['enriched_failed']}")
        logger.info(f"Records persisted:       {self.stats['persisted']}")
        logger.info("=" * 70)


def main():
    """Main entry point for pipeline CLI"""
    parser = argparse.ArgumentParser(
        description="CommonForge Lead Enrichment Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python -m src.pipeline

  # Use custom CSV
  python -m src.pipeline --csv-path data/custom.csv

  # Dry run (no database writes)
  python -m src.pipeline --dry-run

  # Initialize database
  python -m src.pipeline --init-db

  # Reset database (WARNING: deletes all data)
  python -m src.pipeline --reset-db
        """
    )

    parser.add_argument(
        '--csv-path',
        type=Path,
        default=Path('data/companies.csv'),
        help='Path to companies CSV file (default: data/companies.csv)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run pipeline without persisting to database'
    )

    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database tables and exit'
    )

    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='Drop and recreate database tables (WARNING: deletes all data)'
    )

    args = parser.parse_args()

    # Check database connection
    if not check_connection():
        logger.error("❌ Database connection failed. Check DATABASE_URL in .env")
        sys.exit(1)

    # Handle database commands
    if args.init_db:
        logger.info("Initializing database tables...")
        init_db()
        logger.info("✓ Database initialized successfully")
        return

    if args.reset_db:
        confirm = input(
            "⚠️  WARNING: This will delete all data. "
            "Type 'CONFIRM' to proceed: "
        )
        if confirm == "CONFIRM":
            logger.info("Dropping all tables...")
            drop_all_tables()
            logger.info("Recreating tables...")
            init_db()
            logger.info("✓ Database reset complete")
        else:
            logger.info("Reset cancelled")
        return

    # Validate CSV path
    if not args.csv_path.exists():
        logger.error(f"❌ CSV file not found: {args.csv_path}")
        sys.exit(1)

    # Run pipeline
    pipeline = Pipeline(csv_path=args.csv_path, dry_run=args.dry_run)

    try:
        stats = asyncio.run(pipeline.run())
        logger.info("\n✅ Pipeline completed successfully!")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### 6.2 Create Helper Scripts

**File:** `scripts/run_pipeline.sh`

```bash
#!/bin/bash
# Helper script to run the enrichment pipeline

set -e

echo "🚀 Starting CommonForge Pipeline"
echo

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Run: source venv/bin/activate"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "   Copy .env.example to .env and configure it"
    exit 1
fi

# Run pipeline
python -m src.pipeline "$@"
```

**Make executable:**
```bash
chmod +x scripts/run_pipeline.sh
```

---

**File:** `scripts/run_api.sh`

```bash
#!/bin/bash
# Helper script to run the FastAPI server

set -e

echo "🚀 Starting CommonForge API Server"
echo

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Run: source venv/bin/activate"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "   Copy .env.example to .env and configure it"
    exit 1
fi

# Default values
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
RELOAD="${API_RELOAD:-true}"

# Run API server
if [ "$RELOAD" = "true" ]; then
    echo "Starting in development mode (with auto-reload)"
    uvicorn src.api.main:app --host "$HOST" --port "$PORT" --reload
else
    echo "Starting in production mode"
    uvicorn src.api.main:app --host "$HOST" --port "$PORT"
fi
```

**Make executable:**
```bash
chmod +x scripts/run_api.sh
```

---

### 6.3 Create End-to-End Test

**File:** `tests/test_pipeline_e2e.py`

```python
"""
End-to-end pipeline test.

Tests the complete workflow from CSV to database.
"""

import pytest
import asyncio
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.pipeline import Pipeline
from src.db import Base
from src.models import Company


# Use test database
TEST_DB = "sqlite:///./test_pipeline.db"


@pytest.fixture(scope="module")
def test_db():
    """Set up test database"""
    engine = create_engine(TEST_DB)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_pipeline(test_db, monkeypatch):
    """Test complete pipeline execution"""

    # Override database URL for testing
    monkeypatch.setenv("DATABASE_URL", TEST_DB)

    # Run pipeline with sample data
    csv_path = Path("data/companies.csv")

    pipeline = Pipeline(csv_path=csv_path, dry_run=False)
    stats = await pipeline.run()

    # Verify statistics
    assert stats['csv_loaded'] > 0
    assert stats['scraped_success'] + stats['scraped_failed'] == stats['csv_loaded']
    assert stats['persisted'] == stats['csv_loaded']

    # Verify data in database
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()

    try:
        companies = db.query(Company).all()
        assert len(companies) == stats['csv_loaded']

        # Check that some companies were enriched
        enriched = [c for c in companies if c.enrichment_status == 'success']
        assert len(enriched) > 0

        # Verify enriched companies have all required fields
        for company in enriched:
            assert company.icp_fit_score is not None
            assert company.segment is not None
            assert company.primary_use_case is not None
            assert company.risk_flags is not None
            assert company.personalized_pitch is not None

    finally:
        db.close()
```

---

## Verification Steps

### 6.4 Initialize Database

```bash
# Initialize database tables
python -m src.pipeline --init-db

# Expected output:
# Initializing database tables...
# ✓ Database initialized successfully
```

### 6.5 Run Pipeline (Dry Run)

```bash
# Test pipeline without writing to database
python -m src.pipeline --dry-run

# Should complete all steps except database write
```

### 6.6 Run Full Pipeline

```bash
# Run complete pipeline
python -m src.pipeline

# Or using helper script
./scripts/run_pipeline.sh
```

### 6.7 Verify Database

```bash
# Check that data was persisted
psql $DATABASE_URL -c "SELECT company_name, icp_fit_score, segment FROM companies LIMIT 5;"
```

### 6.8 Test API with Enriched Data

```bash
# Start API server
./scripts/run_api.sh

# In another terminal, test endpoints
curl http://localhost:8000/companies?min_score=70
```

---

## Common Issues & Solutions

### Issue 1: Pipeline Fails Mid-Execution

**Problem:** Pipeline crashes and data is partially loaded

**Solution:**
- Add checkpoint/resume logic
- Use transactions for database writes
- Implement idempotent upsert logic (already included)

### Issue 2: Rate Limiting

**Problem:** OpenAI rate limit exceeded

**Solution:**
```python
# Reduce concurrency in .env
CONCURRENT_LLM_CALLS=1

# Or add exponential backoff in llm_chain.py
```

### Issue 3: Memory Issues with Large CSV

**Problem:** Large CSV files cause memory errors

**Solution:**
```python
# Process in batches
for batch in pd.read_csv(csv_path, chunksize=100):
    # Process batch
```

---

## Success Criteria

After completing Phase 6, you should have:

- ✅ Working end-to-end pipeline
- ✅ CLI with all necessary commands
- ✅ Helper scripts for common operations
- ✅ Comprehensive logging
- ✅ Error handling and recovery
- ✅ Successful test run with sample data
- ✅ Data persisted correctly in database

---

## Next Steps

Once Phase 6 is complete:
1. Run full pipeline with sample data
2. Verify data quality in database
3. Test API with enriched data
4. Proceed to **Phase 7: Testing & Quality Assurance**

---

## Time Estimate Breakdown

| Task | Estimated Time |
|------|---------------|
| Implement pipeline.py | 75 min |
| Create helper scripts | 20 min |
| Create e2e tests | 30 min |
| Testing and debugging | 45 min |
| **Total** | **2.75 hours** |
