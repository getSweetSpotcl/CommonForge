#!/bin/bash

# Script to run the CommonForge API server

set -e  # Exit on error

echo "========================================"
echo "CommonForge API Server"
echo "========================================"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not activated"
    echo "   Run: source venv/bin/activate"
    echo ""
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Create .env from .env.example and configure your credentials"
    exit 1
fi

# Check database connection
echo ""
echo "Checking database connection..."
python -c "from src.db import check_connection; import sys; sys.exit(0 if check_connection() else 1)" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
    echo "   Make sure PostgreSQL is running and DATABASE_URL is correct"
    exit 1
fi

echo ""
echo "Starting API server..."
echo "========================================"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🔍 ReDoc: http://localhost:8000/redoc"
echo "❤️  Health: http://localhost:8000/health"
echo "========================================"
echo ""

# Run the API server with uvicorn
# --reload: Auto-reload on code changes (development)
# --host 0.0.0.0: Accept connections from any IP
# --port 8000: Listen on port 8000
uvicorn src.api.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
