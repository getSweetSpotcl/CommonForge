"""
Main pipeline orchestration for CommonForge.

Coordinates the entire ETL process from CSV to enriched database records.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from src.config import settings
from src.db import get_db, init_db, check_connection, SessionLocal
from src.models import Company
from src.ingestion.structured import load_companies_from_csv
from src.ingestion.unstructured import scrape_companies
from src.processing.cleaning import (
    merge_structured_unstructured,
    prepare_for_enrichment,
    apply_enrichment_result
)
from src.processing.llm_chain import enrich_companies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Pipeline:
    """Main ETL pipeline orchestrator"""

    def __init__(
        self,
        csv_path: Path,
        dry_run: bool = False,
        skip_scraping: bool = False,
        skip_enrichment: bool = False,
        max_companies: Optional[int] = None
    ):
        """
        Initialize pipeline.

        Args:
            csv_path: Path to CSV file with company data
            dry_run: If True, don't persist to database
            skip_scraping: If True, skip website scraping
            skip_enrichment: If True, skip LLM enrichment
            max_companies: Maximum number of companies to process (for testing)
        """
        self.csv_path = Path(csv_path)
        self.dry_run = dry_run
        self.skip_scraping = skip_scraping
        self.skip_enrichment = skip_enrichment
        self.max_companies = max_companies

        # Pipeline state
        self.structured_data: List[Dict] = []
        self.scraped_data: List[Dict] = []
        self.merged_data: List[Dict] = []
        self.enriched_data: List[Dict] = []

        # Statistics
        self.stats = {
            'csv_loaded': 0,
            'websites_scraped': 0,
            'scraping_successful': 0,
            'companies_enriched': 0,
            'enrichment_successful': 0,
            'companies_persisted': 0,
            'errors': []
        }

    async def run(self) -> bool:
        """
        Run the complete pipeline.

        Returns:
            bool: True if successful, False otherwise
        """
        start_time = datetime.now()

        logger.info("=" * 70)
        logger.info("COMMONFORGE PIPELINE - STARTING")
        logger.info("=" * 70)
        logger.info(f"CSV Path: {self.csv_path}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"Skip Scraping: {self.skip_scraping}")
        logger.info(f"Skip Enrichment: {self.skip_enrichment}")
        logger.info(f"Max Companies: {self.max_companies or 'All'}")
        logger.info("=" * 70)

        try:
            # Step 1: Load CSV
            if not self._load_csv():
                return False

            # Step 2: Scrape websites
            if not self.skip_scraping:
                if not await self._scrape_websites():
                    logger.warning("Scraping failed, but continuing...")
            else:
                logger.info("⏭️  Skipping website scraping")
                self.scraped_data = []

            # Step 3: Merge data
            if not self._merge_data():
                return False

            # Step 4: Enrich with LLM
            if not self.skip_enrichment:
                if not await self._enrich_companies():
                    logger.warning("Enrichment failed, but continuing...")
            else:
                logger.info("⏭️  Skipping LLM enrichment")

            # Step 5: Persist to database
            if not self.dry_run:
                if not self._persist_to_db():
                    return False
            else:
                logger.info("⏭️  Dry run mode - skipping database persistence")

            # Step 6: Print summary
            self._print_summary(start_time)

            logger.info("=" * 70)
            logger.info("✅ PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}", exc_info=True)
            self.stats['errors'].append(str(e))
            return False

    def _load_csv(self) -> bool:
        """Load companies from CSV file"""
        logger.info("")
        logger.info("📄 STEP 1: Loading CSV Data")
        logger.info("-" * 70)

        try:
            if not self.csv_path.exists():
                logger.error(f"CSV file not found: {self.csv_path}")
                return False

            self.structured_data = load_companies_from_csv(self.csv_path)

            # Apply max_companies limit if specified
            if self.max_companies:
                self.structured_data = self.structured_data[:self.max_companies]

            self.stats['csv_loaded'] = len(self.structured_data)

            logger.info(f"✓ Loaded {len(self.structured_data)} companies from CSV")

            # Show sample
            if self.structured_data:
                sample = self.structured_data[0]
                logger.info(f"  Sample: {sample['company_name']} ({sample['domain']})")

            return True

        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            self.stats['errors'].append(f"CSV loading: {e}")
            return False

    async def _scrape_websites(self) -> bool:
        """Scrape company websites"""
        logger.info("")
        logger.info("🌐 STEP 2: Scraping Websites")
        logger.info("-" * 70)

        try:
            domains = [company['domain'] for company in self.structured_data]
            logger.info(f"Scraping {len(domains)} websites...")

            self.scraped_data = await scrape_companies(domains)

            self.stats['websites_scraped'] = len(self.scraped_data)
            self.stats['scraping_successful'] = sum(
                1 for s in self.scraped_data if s['status'] == 'success'
            )

            success_rate = (self.stats['scraping_successful'] / len(self.scraped_data) * 100) if self.scraped_data else 0

            logger.info(
                f"✓ Scraped {self.stats['websites_scraped']} websites - "
                f"{self.stats['scraping_successful']} successful ({success_rate:.1f}%)"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to scrape websites: {e}")
            self.stats['errors'].append(f"Website scraping: {e}")
            return False

    def _merge_data(self) -> bool:
        """Merge structured and unstructured data"""
        logger.info("")
        logger.info("🔄 STEP 3: Merging Data")
        logger.info("-" * 70)

        try:
            self.merged_data = merge_structured_unstructured(
                self.structured_data,
                self.scraped_data
            )

            logger.info(f"✓ Merged {len(self.merged_data)} company records")

            return True

        except Exception as e:
            logger.error(f"Failed to merge data: {e}")
            self.stats['errors'].append(f"Data merging: {e}")
            return False

    async def _enrich_companies(self) -> bool:
        """Enrich companies with LLM"""
        logger.info("")
        logger.info("🤖 STEP 4: LLM Enrichment")
        logger.info("-" * 70)

        try:
            # Prepare companies for enrichment
            enrichable = prepare_for_enrichment(self.merged_data)

            if not enrichable:
                logger.warning("No companies ready for enrichment (all scraping failed)")
                return True

            logger.info(f"Enriching {len(enrichable)} companies with LLM...")

            # Enrich companies
            enrichment_results = await enrich_companies(enrichable)

            self.stats['companies_enriched'] = len(enrichable)
            self.stats['enrichment_successful'] = sum(
                1 for r in enrichment_results if r.get('icp_fit_score') is not None
            )

            # Apply enrichment results to merged data
            enrichable_domains = {c['domain']: c for c in enrichable}

            for company in self.merged_data:
                if company['domain'] in enrichable_domains:
                    # Find corresponding enrichment result
                    idx = next(
                        i for i, c in enumerate(enrichable)
                        if c['domain'] == company['domain']
                    )
                    enrichment = enrichment_results[idx]

                    # Apply if successful
                    if enrichment.get('icp_fit_score') is not None:
                        company.update({
                            'icp_fit_score': enrichment['icp_fit_score'],
                            'segment': enrichment['segment'],
                            'primary_use_case': enrichment['primary_use_case'],
                            'risk_flags': enrichment['risk_flags'],
                            'personalized_pitch': enrichment['personalized_pitch'],
                            'enrichment_status': 'success',
                            'enrichment_error': None
                        })
                    else:
                        company.update({
                            'enrichment_status': 'failed',
                            'enrichment_error': enrichment.get('error', 'Unknown error')
                        })

            success_rate = (self.stats['enrichment_successful'] / self.stats['companies_enriched'] * 100) if self.stats['companies_enriched'] else 0

            logger.info(
                f"✓ Enriched {self.stats['companies_enriched']} companies - "
                f"{self.stats['enrichment_successful']} successful ({success_rate:.1f}%)"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to enrich companies: {e}")
            self.stats['errors'].append(f"LLM enrichment: {e}")
            return False

    def _persist_to_db(self) -> bool:
        """Persist merged and enriched data to database"""
        logger.info("")
        logger.info("💾 STEP 5: Persisting to Database")
        logger.info("-" * 70)

        try:
            # Check database connection
            if not check_connection():
                logger.error("Database connection failed")
                return False

            # Initialize database (create tables if needed)
            init_db()

            db = SessionLocal()

            try:
                for company_data in self.merged_data:
                    # Check if company already exists (by domain)
                    existing = db.query(Company).filter(
                        Company.domain == company_data['domain']
                    ).first()

                    if existing:
                        # Update existing company
                        for key, value in company_data.items():
                            setattr(existing, key, value)
                        logger.debug(f"Updated: {company_data['company_name']}")
                    else:
                        # Create new company
                        company = Company(**company_data)
                        db.add(company)
                        logger.debug(f"Created: {company_data['company_name']}")

                    self.stats['companies_persisted'] += 1

                # Commit all changes
                db.commit()

                logger.info(f"✓ Persisted {self.stats['companies_persisted']} companies to database")

                return True

            except Exception as e:
                db.rollback()
                raise e

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to persist to database: {e}")
            self.stats['errors'].append(f"Database persistence: {e}")
            return False

    def _print_summary(self, start_time: datetime):
        """Print pipeline execution summary"""
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("")
        logger.info("Statistics:")
        logger.info(f"  • Companies loaded from CSV: {self.stats['csv_loaded']}")
        logger.info(f"  • Websites scraped: {self.stats['websites_scraped']}")
        logger.info(f"  • Scraping successful: {self.stats['scraping_successful']}")
        logger.info(f"  • Companies enriched: {self.stats['companies_enriched']}")
        logger.info(f"  • Enrichment successful: {self.stats['enrichment_successful']}")
        logger.info(f"  • Companies persisted: {self.stats['companies_persisted']}")

        if self.stats['errors']:
            logger.info("")
            logger.info("Errors:")
            for error in self.stats['errors']:
                logger.info(f"  ✗ {error}")

        logger.info("")

        # Show sample enriched companies
        if self.merged_data:
            enriched = [c for c in self.merged_data if c.get('enrichment_status') == 'success']
            if enriched:
                logger.info("Sample Enriched Companies:")
                logger.info("-" * 70)
                for company in enriched[:3]:  # Show top 3
                    logger.info(f"\n  {company['company_name']} ({company['domain']})")
                    logger.info(f"  ICP Score: {company.get('icp_fit_score', 'N/A')}/100")
                    logger.info(f"  Segment: {company.get('segment', 'N/A')}")
                    logger.info(f"  Use Case: {company.get('primary_use_case', 'N/A')}")
                    if company.get('risk_flags'):
                        logger.info(f"  Risk Flags: {', '.join(company['risk_flags'])}")


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CommonForge Pipeline - AI-Powered B2B Lead Scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python -m src.pipeline data/companies.csv

  # Dry run (no database persistence)
  python -m src.pipeline data/companies.csv --dry-run

  # Skip enrichment (for testing scraping)
  python -m src.pipeline data/companies.csv --skip-enrichment

  # Process only first 2 companies
  python -m src.pipeline data/companies.csv --max-companies 2
        """
    )

    parser.add_argument(
        'csv_path',
        type=str,
        help='Path to CSV file with company data'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run pipeline without persisting to database'
    )

    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Skip website scraping step'
    )

    parser.add_argument(
        '--skip-enrichment',
        action='store_true',
        help='Skip LLM enrichment step'
    )

    parser.add_argument(
        '--max-companies',
        type=int,
        help='Maximum number of companies to process (for testing)'
    )

    args = parser.parse_args()

    # Create and run pipeline
    pipeline = Pipeline(
        csv_path=args.csv_path,
        dry_run=args.dry_run,
        skip_scraping=args.skip_scraping,
        skip_enrichment=args.skip_enrichment,
        max_companies=args.max_companies
    )

    success = await pipeline.run()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
