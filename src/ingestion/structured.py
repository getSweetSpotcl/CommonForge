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

    REQUIRED_COLUMNS = ["company_name", "domain", "country", "employee_count", "industry_raw"]

    def __init__(self, csv_path: Path):
        """
        Initialize CSV ingestor.

        Args:
            csv_path: Path to CSV file
        """
        self.csv_path = Path(csv_path)

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        if not self.csv_path.suffix.lower() == ".csv":
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
        df["domain"] = df["domain"].apply(self._normalize_domain)

        # Clean company name
        df["company_name"] = df["company_name"].str.strip()

        # Clean country
        df["country"] = df["country"].str.strip()

        # Ensure employee_count is integer
        df["employee_count"] = pd.to_numeric(df["employee_count"], errors="coerce")
        df = df.dropna(subset=["employee_count"])
        df["employee_count"] = df["employee_count"].astype(int)

        # Remove duplicates by domain (keep first occurrence)
        df = df.drop_duplicates(subset=["domain"], keep="first")

        # Remove invalid entries
        df = df[df["employee_count"] > 0]
        df = df[df["domain"].str.len() > 0]

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
        domain = domain.replace("http://", "").replace("https://", "")

        # Remove www
        domain = domain.replace("www.", "")

        # Remove trailing slash
        domain = domain.rstrip("/")

        # Remove path (keep only domain)
        domain = domain.split("/")[0]

        # Remove port if present
        domain = domain.split(":")[0]

        return domain

    def to_dicts(self, df: pd.DataFrame) -> List[Dict]:
        """
        Convert DataFrame to list of dictionaries.

        Args:
            df: DataFrame to convert

        Returns:
            List[Dict]: List of company records
        """
        return df.to_dict("records")


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


# Test script
if __name__ == "__main__":
    from pathlib import Path

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
