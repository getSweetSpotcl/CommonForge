# Frontend Implementation Plan: Vue 3 + Tailwind CSS

**Date:** 2025-11-13
**Status:** In Progress
**Tech Stack:** Vue 3 (CDN), Tailwind CSS (Play CDN), Chart.js

## Overview

Building a simple, reactive frontend application for CommonForge that allows users to:
1. Upload CSV files with company data
2. Monitor processing progress in real-time
3. View enriched results in sortable/filterable table
4. Explore statistics dashboard with charts

## Technology Decisions

### Why Vue 3 + Tailwind?
- **No build step required** - Use CDN versions for rapid development
- **Reactive by default** - Auto-updates UI when data changes
- **Easy to learn** - Template syntax is HTML-based
- **Tailwind CSS** - Rapid UI development with utility classes
- **Perfect for small-medium apps** - Our exact use case

### Architecture
Single-page application (SPA) with 4 main views:
- **Upload** - Drag & drop CSV files with preview
- **Processing** - Real-time progress tracking
- **Companies** - Sortable table with filters
- **Statistics** - Dashboard with metrics and charts

---

## Phase 1: Backend API Endpoints (2-3 hours)

### Files to Modify
- `src/api/main.py` - Add upload endpoint, job tracking, static serving
- `src/pipeline.py` - Add background execution and progress callbacks

### New Endpoints

#### 1. POST /api/upload
```python
@app.post("/api/upload")
async def upload_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    # 1. Validate CSV file
    # 2. Save temporarily
    # 3. Generate job_id (UUID)
    # 4. Start pipeline in background
    # 5. Return job_id for tracking
```

#### 2. GET /api/jobs/{job_id}
```python
@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    # Return job status from jobs dict
    # Status: queued, processing, completed, failed
    # Progress: { step, current, total, message }
```

#### 3. Static File Serving
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

### Job Tracking System
- In-memory dictionary to store job status
- Structure: `{ job_id: { status, progress, result, error } }`
- For production: Use Redis

### Pipeline Modifications
- Add `progress_callback` parameter
- Call callback at each step (Load, Scrape, Enrich, Persist)
- Make pipeline async-compatible
- Return structured result for API

---

## Phase 2: Frontend Structure (30 mins)

### Directory Structure
```
frontend/
├── index.html          # Main SPA file (~400-500 lines)
├── app.js              # Vue app logic (optional split)
└── components.js       # Vue components (optional split)
```

### Initial Setup
Single `index.html` file containing:
1. CDN imports (Vue 3, Tailwind, Chart.js, Axios)
2. HTML structure with all views
3. Vue components (inline)
4. Application logic and state

### CDN Resources
```html
<!-- Vue 3 -->
<script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>

<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- Axios -->
<script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
```

---

## Phase 3: Core Components (4-5 hours)

### Component 1: UploadView (1 hour)

**Features:**
- Drag-and-drop zone (styled with Tailwind)
- File validation (CSV only, max 10MB)
- Preview table showing first 5 rows
- Submit button to upload and start processing

**Vue Data:**
```javascript
{
  selectedFile: null,
  previewData: [],
  uploading: false
}
```

**Methods:**
- `handleFileSelect(file)` - Validate and preview
- `uploadFile()` - POST to /api/upload
- `parseCSVPreview(file)` - Show first 5 rows

### Component 2: ProcessingView (1 hour)

**Features:**
- Animated progress bar
- Current step indicator (Loading → Scraping → Enriching → Saving)
- Poll job status every 2 seconds
- Auto-navigate to results when complete

**Vue Data:**
```javascript
{
  jobId: null,
  status: 'queued',
  progress: { current: 0, total: 0, step: '', message: '' },
  pollInterval: null
}
```

**Methods:**
- `startMonitoring(jobId)` - Begin polling
- `pollStatus()` - GET /api/jobs/{job_id}
- `updateProgress(data)` - Update UI
- `handleCompletion()` - Navigate to results

### Component 3: CompaniesView (2 hours)

**Features:**
- Reactive table with all companies
- Search/filter controls (country, segment, min score)
- Sortable columns (click header to sort)
- Pagination (25/50/100 per page)
- Click row to open detail modal
- Color-coded ICP scores (green >80, yellow 50-80, red <50)

**Vue Data:**
```javascript
{
  companies: [],
  filters: { search: '', country: '', segment: '', minScore: 0 },
  sortBy: 'icp_fit_score',
  sortOrder: 'desc',
  currentPage: 1,
  perPage: 25,
  selectedCompany: null
}
```

**Computed Properties:**
- `filteredCompanies` - Apply filters
- `sortedCompanies` - Apply sorting
- `paginatedCompanies` - Apply pagination
- `totalPages` - Calculate total pages

**Methods:**
- `fetchCompanies()` - GET /companies
- `applyFilters()` - Update filtered list
- `sortByColumn(column)` - Toggle sort
- `showDetail(company)` - Open modal

### Component 4: StatsView (1 hour)

**Features:**
- Metric cards (total, enriched, average score)
- Segment distribution pie chart
- Country distribution bar chart
- Top 10 companies by score
- Auto-refresh every 30 seconds

**Vue Data:**
```javascript
{
  stats: {
    total_companies: 0,
    enriched_companies: 0,
    average_icp_score: 0,
    by_segment: {},
    by_country: {},
    top_companies: []
  }
}
```

**Methods:**
- `fetchStats()` - GET /stats
- `renderSegmentChart()` - Chart.js pie chart
- `renderCountryChart()` - Chart.js bar chart
- `autoRefresh()` - Refresh every 30s

---

## Phase 4: State Management (1 hour)

### Global Vue State
```javascript
{
  // Navigation
  currentView: 'upload', // upload, processing, companies, stats

  // Data
  companies: [],
  stats: {},

  // UI State
  loading: false,
  error: null,

  // Upload State
  currentJob: null,

  // Modal
  showModal: false,
  selectedCompany: null
}
```

### API Service
```javascript
const api = {
  baseURL: 'http://localhost:8000',

  uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${this.baseURL}/api/upload`, formData);
  },

  getJobStatus(jobId) {
    return axios.get(`${this.baseURL}/api/jobs/${jobId}`);
  },

  getCompanies(filters = {}) {
    return axios.get(`${this.baseURL}/companies`, { params: filters });
  },

  getStats() {
    return axios.get(`${this.baseURL}/stats`);
  },

  getCompany(id) {
    return axios.get(`${this.baseURL}/companies/${id}`);
  }
}
```

---

## Phase 5: UI Polish (1 hour)

### Loading States
- Skeleton loaders for tables
- Spinner for data fetching
- Disabled buttons during operations

### Error Handling
- Toast notifications for errors
- Retry buttons
- Graceful degradation

### Responsive Design
- Mobile breakpoints (Tailwind: sm, md, lg, xl)
- Collapsible filters on mobile
- Stacked cards on small screens

### Animations
- Smooth view transitions
- Progress bar animation
- Modal fade in/out
- Hover effects

---

## Key Features Summary

✅ **Upload**
- Drag-and-drop CSV files
- Instant preview of data
- Validation and error messages

✅ **Processing**
- Real-time progress bar
- Step-by-step status updates
- Auto-navigate when complete

✅ **Companies List**
- Sortable columns
- Multi-filter (search, country, segment, score)
- Pagination
- Detail modal with full info

✅ **Statistics**
- Metric cards
- Chart.js visualizations
- Top performers list
- Auto-refresh

✅ **Modern UI**
- Tailwind CSS styling
- Responsive design
- Smooth animations
- Professional look

---

## Implementation Timeline

| Phase | Task | Time |
|-------|------|------|
| 1 | Backend API endpoints | 2-3 hours |
| 2 | Frontend structure | 30 mins |
| 3 | Upload component | 1 hour |
| 3 | Processing monitor | 1 hour |
| 3 | Companies table | 2 hours |
| 3 | Stats dashboard | 1 hour |
| 4 | State management | 1 hour |
| 5 | UI polish | 1 hour |
| **Total** | | **8-10 hours** |

---

## Development Workflow

1. Start backend: `source venv/bin/activate && uvicorn src.api.main:app --reload`
2. Open browser: `http://localhost:8000`
3. Edit `frontend/index.html`
4. Refresh browser (no build needed!)

---

## Future Enhancements (Optional)

- WebSocket for real-time updates (instead of polling)
- Export results to CSV
- Bulk delete/edit companies
- User authentication
- Dark mode toggle
- Advanced filtering (date ranges, custom queries)
- Split into separate JS modules for better organization
- Add Vite build step for production optimization

---

## Success Metrics

- ✅ Upload CSV and start processing in < 3 clicks
- ✅ See progress updates in real-time
- ✅ View results table within 5 seconds of completion
- ✅ Filter/sort companies without page reload
- ✅ Works on mobile devices
- ✅ No build step required for development

---

**Status:** Ready to implement Phase 1
