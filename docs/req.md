
1) README.md
# 🧠 AI-Powered B2B Lead Scoring Prototype  
**Author:** Gustavo Cortínez  
**Role:** Principal AI Engineer Candidate  

---

## 1. Overview

This prototype demonstrates how I design and deliver an **AI-powered workflow** that combines structured and unstructured data, enriches it using a Large Language Model (LLM), and exposes the results through a modern API.

### 💡 Use Case

Given a list of companies, the system:

1. Pulls **structured data** from a CSV containing:
   - `company_name`
   - `domain`
   - `country`
   - `employee_count`
   - `industry_raw`

2. Fetches **unstructured data** by scraping the public website of each company and extracting the main textual content.

3. Uses an **LLM (via LangChain)** to enrich each company with:
   - `icp_fit_score` (0–100): how well this company fits a target ICP for an AI automation platform.
   - `segment`: `"SMB" | "Mid-Market" | "Enterprise"`.
   - `primary_use_case`: short description of the key use case.
   - `risk_flags`: list of potential issues or caveats.
   - `personalized_pitch`: one-sentence, tailored sales pitch.

4. Stores the enriched data in **PostgreSQL**.

5. Exposes the results through a **FastAPI** interface for querying and inspection.

This pattern is representative of how I would build a production-ready enrichment pipeline: modular, asynchronous where it matters, and easy to extend or scale.

---

## 2. High-Level Architecture

### Components

| Layer                      | Description                                                  | Technologies                       |
|----------------------------|--------------------------------------------------------------|------------------------------------|
| Ingestion (Structured)     | Reads and normalizes CSV with company metadata.              | Pandas                             |
| Ingestion (Unstructured)   | Scrapes public websites and extracts main text.              | HTTPX, BeautifulSoup               |
| Processing / Enrichment    | Uses an LLM to classify and enrich companies.                | LangChain, OpenAI                  |
| Persistence                | Stores enriched company records.                             | SQLAlchemy, PostgreSQL             |
| Orchestration              | Defines and runs the end-to-end workflow.                    | Async Python                       |
| Serving Layer              | REST API for querying enriched companies.                    | FastAPI, Pydantic                  |

### Data Flow

```text
1) companies.csv (structured)
     │
     ▼
2) Structured ingestion (Pandas)
     │
     ├──► 3) Website scraping (HTTPX + BeautifulSoup) ─► website_text_snippet (unstructured)
     │
     ▼
4) Join structured + unstructured data
     │
     ▼
5) LLM enrichment (LangChain chain → JSON output)
     │
     ▼
6) PostgreSQL (SQLAlchemy models)
     │
     ▼
7) FastAPI (query enriched companies via REST)

3. Why This Architecture
LangChain
Encapsulates the prompt, model, and JSON parsing into a composable chain.


Makes it easy to:


Switch models (e.g., different providers or tiers).


Add tools or extra steps (e.g., RAG, tools for external APIs).


Enforce structured outputs instead of free-form text.


FastAPI
Async-friendly, high-performance Python web framework.


Pydantic-based request/response models with type hints.


Auto-generates OpenAPI/Swagger docs, simplifying collaboration with other teams and clients.


PostgreSQL
Realistic choice for any non-trivial production scenario (multi-user, concurrent reads/writes).


Easy to move to managed services such as AWS RDS, GCP Cloud SQL, or Azure Database for PostgreSQL.


Supports indexing, complex queries, and schema evolution.


Separation of Concerns
The enrichment pipeline (ingestion + scraping + LLM calls) is implemented as a standalone job (pipeline.py).


The serving layer (FastAPI) is a separate component that only reads from the database.


In a real environment I would schedule the pipeline as a batch or event-driven process (cron, Airflow, Prefect, n8n), while the API remains a stateless, stable interface for downstream consumers.

4. Project Structure
.
├── README.md
├── requirements.txt
├── data
│   └── companies.csv
├── src
│   ├── config.py          # environment configuration (DB URL, API keys)
│   ├── db.py              # SQLAlchemy engine + session factory + Base
│   ├── models.py          # ORM schema (Company)
│   ├── schemas.py         # Pydantic models for API responses
│   ├── ingestion
│   │   ├── structured.py  # CSV loading and basic cleaning
│   │   └── unstructured.py# async website fetching and HTML parsing
│   ├── processing
│   │   ├── cleaning.py    # joining structured and unstructured data
│   │   └── llm_chain.py   # LangChain LLM enrichment pipeline
│   ├── pipeline.py        # end-to-end orchestration script
│   └── api
│       └── main.py        # FastAPI application
└── scripts
    └── run_pipeline.sh    # optional helper script

5. Sample Data (data/companies.csv)
For the demo, the repository includes a small CSV with 5 real SaaS companies:
company_name,domain,country,employee_count,industry_raw
HubSpot,hubspot.com,USA,7400,Marketing & CRM Software
Asana,asana.com,USA,1900,Work Management Software
Monday.com,monday.com,Israel,1800,Work OS / Collaboration
Notion,notion.so,USA,600,Knowledge Management / Productivity
Intercom,intercom.com,USA,1300,Customer Messaging Platform
The pipeline will:
Load this CSV.


Fetch each company’s homepage.


Extract the main textual content.


Enrich each row using the LLM.


Persist the results in PostgreSQL.



6. Setup Instructions
6.1. Prerequisites
Python 3.11+


A running PostgreSQL instance (local or remote)


An OpenAI API key (or compatible LLM provider, configured via LangChain)


6.2. Install Dependencies
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_NAME>
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
6.3. Environment Configuration
Create a .env file in the project root:
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname
OPENAI_API_KEY=sk-...
You can also export these variables directly in your shell if you prefer.

7. Running the Workflow
7.1. Create Database Tables
The Company table is defined using SQLAlchemy in src/models.py.
 To create the table(s), run:
python -m src.pipeline --init-db
(If you prefer, you can also call Base.metadata.create_all(bind=engine) from a small separate script.)
7.2. Run the End-to-End Pipeline
This command:
Loads data/companies.csv.


Fetches and parses the homepage for each domain.


Joins structured + unstructured data.


Calls the LangChain LLM chain for each company.


Persists the enriched records to PostgreSQL.


python -m src.pipeline
Depending on the model used and rate limits, this might take a short while for all companies.

8. Running the API
Start the FastAPI server:
uvicorn src.api.main:app --reload
Then open the interactive docs:
Swagger UI: http://localhost:8000/docs


OpenAPI JSON: http://localhost:8000/openapi.json



9. API Endpoints
9.1. GET /companies
List enriched companies with optional filters:
Query parameters:
min_score (int, default 0): minimum icp_fit_score


country (string, optional)


segment (string, optional: "SMB", "Mid-Market", "Enterprise")


Example:
curl "http://localhost:8000/companies?min_score=70&segment=Mid-Market"

9.2. GET /companies/{company_id}
Retrieve a single enriched company by ID.
Example:
curl "http://localhost:8000/companies/1"
Sample JSON Response:
{
  "company_name": "HubSpot",
  "domain": "hubspot.com",
  "country": "USA",
  "employee_count": 7400,
  "industry_raw": "Marketing & CRM Software",
  "website_text_snippet": "HubSpot provides a full stack of software for marketing, sales, and customer service...",
  "icp_fit_score": 91,
  "segment": "Enterprise",
  "primary_use_case": "AI-powered marketing and sales automation",
  "risk_flags": ["Complex enterprise stack"],
  "personalized_pitch": "HubSpot could leverage our AI automation platform to orchestrate cross-channel workflows and reduce manual operational overhead."
}

10. Implementation Highlights
10.1. Ingestion & Scraping
CSV loading via Pandas.


Domain normalization (http/https, www, trimming).


Async fetching of websites using HTTPX.


HTML parsing and text extraction using BeautifulSoup.


Text truncated to a safe length for LLM prompts.


10.2. LLM Enrichment with LangChain
In processing/llm_chain.py:
A ChatPromptTemplate describes:


The structured company data (name, country, size, industry).


The website text snippet.


The expected JSON schema (fields for score, segment, etc.).


A JsonOutputParser enforces structured output and reduces parsing errors.


An async chain.ainvoke(...) call returns a Python dict ready to be validated and persisted.


10.3. Persistence
The Company SQLAlchemy model stores:
Raw structured fields.


Website text snippet.


Enriched fields:


icp_fit_score


segment


primary_use_case


risk_flags (stored as a serialized string or JSON)


personalized_pitch


created_at timestamp.


10.4. Serving Layer (FastAPI)
Endpoints defined in src/api/main.py.


Uses Pydantic response models defined in schemas.py.


Supports filtered queries over icp_fit_score, country, and segment.


Can be easily extended with pagination, authentication, or additional filters.



11. Scaling and Future Work
If this prototype were to evolve into a production service, I would:
Data Scale


Move enrichment into a job queue (Celery, RQ, or cloud-native queues).


Introduce batching and caching of LLM requests per domain.


Add structured logging and error handling for each stage.


Model Scale


Route by company value (e.g., use a cheaper model for low-value leads, and a more capable model for key accounts).


Experiment with domain-specific finetuning or prompt tuning.


Architecture


Split into microservices: ingestion, enrichment, serving.


Deploy API and workers in containers (Docker/Kubernetes).


Add feature flags and A/B testing for prompt changes.


Observability


Metrics: leads processed/hour, LLM latency, error rate, distribution of ICP scores.


Dashboards for enrichment coverage and data quality.



12. Video Walkthrough (Outline)
The accompanying 5–10 minute video explains:
The use case and data sources (CSV + websites).


The architecture and rationale (LangChain, FastAPI, Postgres, async).


A short code walkthrough of the pipeline and the LLM chain.


A demo of the API endpoints with real enriched companies.


How I would scale and productionize this pattern.



13. Tech Stack
Category
Tool / Library
Language
Python 3.11
LLM Orchestration
LangChain
Model Provider
OpenAI (e.g. gpt-4.1-mini or similar)
Web Framework
FastAPI
ORM
SQLAlchemy
Database
PostgreSQL
HTTP Client
HTTPX
HTML Parsing
BeautifulSoup4
Data Processing
Pandas
Config
Pydantic Settings
ASGI Server
Uvicorn


14. License
MIT License – for evaluation and demonstration purposes.

---

## 2) `requirements.txt`

```txt
fastapi
uvicorn
pydantic
pydantic-settings
sqlalchemy
psycopg2-binary
pandas
httpx
beautifulsoup4
langchain
langchain-openai
openai
python-dotenv
(You can pin versions later if you want, but for the test this “floating” list is fine.)

3) data/companies.csv
company_name,domain,country,employee_count,industry_raw
HubSpot,hubspot.com,USA,7400,Marketing & CRM Software
Asana,asana.com,USA,1900,Work Management Software
Monday.com,monday.com,Israel,1800,Work OS / Collaboration
Notion,notion.so,USA,600,Knowledge Management / Productivity
Intercom,intercom.com,USA,1300,Customer Messaging Platform
Con esto ya tienes:
Un README totalmente listo para GitHub (en inglés, alineado con el desafío).


Dependencias mínimas.


Datos de ejemplo con 5 empresas reales para tu demo.


Si quieres, en el siguiente paso puedo ayudarte a escribir stubs de código para pipeline.py y api/main.py para que sólo tengas que completar detalles y configurar tu Postgres.

