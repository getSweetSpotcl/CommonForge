# CommonForge: AI-Powered B2B Lead Scoring

An AI-powered lead scoring system that combines structured company data with unstructured web content to generate intelligent ICP (Ideal Customer Profile) fit scores and personalized sales insights.

## Features

- **Multi-Source Data Ingestion:** CSV + web scraping
- **AI-Powered Enrichment:** LLM-based analysis using LangChain
- **Intelligent Scoring:** 0-100 ICP fit score for each company
- **Segment Classification:** Automatic SMB/Mid-Market/Enterprise categorization
- **Personalized Insights:** Custom sales pitches and risk flags
- **REST API:** FastAPI-powered API with filtering and search

## Tech Stack

- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **LLM Framework:** LangChain
- **LLM Provider:** OpenAI GPT-4
- **HTTP Client:** HTTPX (async)
- **HTML Parsing:** BeautifulSoup4
- **Data Processing:** Pandas

## Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (local or remote)
- OpenAI API key

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd CommonForge
   ```

2. **Create virtual environment:**

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database:**

   ```bash
   # Create PostgreSQL database
   createdb commonforge

   # Initialize tables
   python -m src.pipeline --init-db
   ```

### Usage

**Run the enrichment pipeline:**

```bash
python -m src.pipeline
```

**Start the API server:**

```bash
uvicorn src.api.main:app --reload
```

**Access the API:**

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

### API Endpoints

**List companies with filters:**

```bash
GET /companies?min_score=70&segment=Mid-Market
```

**Get specific company:**

```bash
GET /companies/{company_id}
```

## Development

**Run tests:**

```bash
pytest
```

**Run tests with coverage:**

```bash
pytest --cov=src --cov-report=html
```

**Code formatting:**

```bash
black src/ tests/
```

**Linting:**

```bash
flake8 src/ tests/
mypy src/
```

## Project Structure

```text
CommonForge/
├── src/              # Source code
│   ├── api/         # FastAPI application
│   ├── ingestion/   # Data ingestion (CSV + web scraping)
│   ├── processing/  # LLM enrichment pipeline
│   ├── config.py    # Configuration management
│   ├── db.py        # Database connection
│   ├── models.py    # SQLAlchemy models
│   ├── schemas.py   # Pydantic schemas
│   └── pipeline.py  # Main orchestration
├── tests/           # Test suite
├── data/            # Sample data
├── plan/            # Implementation plans
└── scripts/         # Helper scripts
```

## Architecture

See [plan/01-architecture.md](plan/01-architecture.md) for detailed technical architecture.

## License

MIT License - for evaluation and demonstration purposes.

## Author

Gustavo Cortínez - Principal AI Engineer Candidate
