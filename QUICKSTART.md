# CommonForge Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your credentials
nano .env
```

**Required variables:**
- `DATABASE_URL` - Your PostgreSQL connection string
- `OPENAI_API_KEY` - Your OpenAI API key

### 2. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### 3. Start the Application

```bash
./scripts/start.sh
```

This starts the **complete application** (backend API + frontend UI) at:
- **Frontend:** http://localhost:8000/app/
- **API Docs:** http://localhost:8000/docs

---

## 📊 Using the Web UI

### Upload Companies

1. Open http://localhost:8000/app/
2. Click "Upload" tab
3. Drag & drop `data/companies.csv` (or your own CSV file)
4. Preview the data
5. Click "Process Companies"

### Monitor Progress

- Watch the real-time progress bar
- See which step is running (Loading, Scraping, Enriching, Saving)
- Auto-redirects to results when complete

### View Results

**Companies Tab:**
- Browse all enriched companies in a sortable table
- Filter by country, segment, or ICP score
- Click any row to see full details including:
  - ICP fit score (0-100)
  - Segment classification
  - Primary use case
  - Personalized sales pitch
  - Risk flags

**Statistics Tab:**
- See total companies and enrichment rate
- View average ICP score
- Analyze segment distribution (pie chart)
- Analyze country distribution (bar chart)
- See top 10 companies by score

---

## 🎯 Alternative Usage Options

### Option 1: CLI Pipeline

```bash
# Process sample data
./scripts/run_pipeline.sh data/companies.csv

# Process with limits (save costs)
./scripts/run_pipeline.sh data/companies.csv --max-companies 2

# Dry run (no database save)
./scripts/run_pipeline.sh data/companies.csv --dry-run
```

### Option 2: REST API Only

```bash
# Start API server
./scripts/run_api.sh

# Query companies
curl http://localhost:8000/companies

# Filter by segment
curl "http://localhost:8000/companies?segment=Enterprise"

# Get statistics
curl http://localhost:8000/stats
```

---

## 📝 CSV File Format

Your CSV must have these columns:

```csv
company_name,domain,country,employee_count,industry_raw
Acme Corp,acme.com,USA,500,SaaS Platform
TechStart,techstart.io,UK,50,Developer Tools
```

---

## ✅ Verification

Check that everything is working:

```bash
# 1. Test config
python -c "from src.config import settings; print('✅ Config loaded')"

# 2. Test database
python -c "from src.db import check_connection; print('✅ DB Connected' if check_connection() else '❌ DB Failed')"

# 3. Test API
curl http://localhost:8000/health
```

---

## 🐛 Common Issues

### "Database connection failed"

```bash
# Check PostgreSQL is running
pg_isready

# Verify DATABASE_URL in .env
grep DATABASE_URL .env
```

### "OpenAI API error"

```bash
# Verify API key
grep OPENAI_API_KEY .env

# Check you have credits
# Go to: https://platform.openai.com/usage
```

### "Frontend not loading"

```bash
# Check server is running
curl http://localhost:8000/app/

# Should return HTML (HTTP 200)
```

---

## 📚 More Help

- **Detailed Frontend Guide:** [FRONTEND-GUIDE.md](FRONTEND-GUIDE.md)
- **Full Documentation:** [README.md](README.md)
- **API Documentation:** http://localhost:8000/docs (when server running)
- **Implementation Plan:** [plans/frontend-vue-tailwind.md](plans/frontend-vue-tailwind.md)

---

## 🎉 You're Ready!

Open http://localhost:8000/app/ and start scoring leads!

**Sample workflow:**
1. Upload `data/companies.csv`
2. Wait ~1-2 minutes for processing
3. Browse enriched companies
4. Filter for high ICP scores (≥80)
5. View personalized pitches
6. Export or query via API

Happy lead scoring! 🚀
