# CommonForge Frontend Guide

## Quick Start

The frontend is now running! Access it at:

**http://localhost:8000/app/**

## Features

### 1. Upload View
- **Drag & drop** CSV files or click to browse
- **Preview** first 5 rows before processing
- **Submit** to start the pipeline

### 2. Processing View
- **Real-time progress** bar with percentage
- **Status updates** for each pipeline step:
  - Loading CSV
  - Scraping websites
  - Enriching with AI
  - Saving to database
- **Auto-navigate** to results when complete

### 3. Companies View
- **Sortable table** (click column headers)
- **Filters:**
  - Search by company name or domain
  - Filter by country
  - Filter by segment (SMB, Mid-Market, Enterprise)
  - Filter by minimum ICP score (slider)
- **Pagination** (25 companies per page)
- **Click row** to view full company details in modal
- **Color-coded scores:**
  - Green: 80-100 (excellent fit)
  - Yellow: 50-79 (good fit)
  - Red: 0-49 (poor fit)

### 4. Statistics Dashboard
- **Metric cards:**
  - Total companies
  - Enriched companies + rate
  - Average ICP score
- **Charts:**
  - Segment distribution (pie chart)
  - Country distribution (bar chart)
- **Top 10** companies by ICP score

## How to Use

### Step 1: Upload Data
1. Go to the Upload tab
2. Drag & drop your CSV file (or click to browse)
3. Required CSV columns:
   - `company_name`
   - `domain`
   - `country`
   - `employee_count`
   - `industry_raw`
4. Preview the data
5. Click "Process Companies"

### Step 2: Monitor Progress
- The app automatically switches to Processing view
- Watch real-time progress updates
- Wait for completion (usually 1-2 minutes for 5 companies)

### Step 3: View Results
- After processing, the app auto-navigates to Companies view
- Browse enriched company data
- Use filters to find high-value leads
- Click "View Details" to see full enrichment data including personalized pitches

### Step 4: Analyze Statistics
- Go to Statistics tab
- View overall performance metrics
- Analyze segment and country distributions
- Review top-performing companies

## Technical Details

### Technology Stack
- **Vue 3** (via CDN - no build required)
- **Tailwind CSS** (utility-first styling)
- **Chart.js** (data visualizations)
- **FastAPI backend** (Python)

### Architecture
```
Frontend (Vue 3)
    ↓ HTTP/REST
FastAPI Server
    ↓
Pipeline (async background task)
    ↓
PostgreSQL Database
```

### API Endpoints Used
- `POST /api/upload` - Upload CSV and start processing
- `GET /api/jobs/{job_id}` - Poll job status
- `GET /companies` - Fetch all companies (with filters)
- `GET /companies/{id}` - Get single company details
- `GET /stats` - Get statistics

## Troubleshooting

### Frontend not loading?
Check that server is running:
```bash
curl http://localhost:8000/app/
```

Should return HTTP 200.

### Upload failing?
- Ensure CSV has required columns
- Check file size (< 10MB)
- Verify .csv extension

### Processing stuck?
- Check server logs
- Verify OpenAI API key is set
- Check database connection

### No companies showing?
- Make sure you've processed at least one CSV file
- Try clicking "Companies" tab to refresh
- Check browser console for errors

## Sample Data

You can test with the included sample file:
```
data/companies.csv
```

This contains 5 sample B2B SaaS companies.

## Development

### File Structure
```
frontend/
└── index.html          # Single-file Vue app
```

### Making Changes
1. Edit `frontend/index.html`
2. Refresh browser (no build needed!)
3. Changes are live immediately

### Adding Features
The app uses a simple reactive pattern:
- Data is stored in Vue `data()`
- Methods manipulate data
- UI auto-updates via Vue reactivity
- All in one file for simplicity

## Next Steps

Optional enhancements:
- Add WebSocket for real-time updates (instead of polling)
- Export results to CSV
- Batch delete/edit companies
- User authentication
- Dark mode
- Advanced filtering
- Split into separate modules
- Add Vite for production build

## Support

For issues or questions:
- Check the main README.md
- Review API docs at http://localhost:8000/docs
- Check browser console for errors
- Review server logs

---

**Happy lead scoring!** 🚀
