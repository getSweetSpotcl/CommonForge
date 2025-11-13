#!/bin/bash

# Script to run the CommonForge pipeline

set -e  # Exit on error

echo "========================================"
echo "CommonForge Pipeline Runner"
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

# Default CSV path
CSV_PATH="${1:-data/companies.csv}"

# Check if CSV file exists
if [ ! -f "$CSV_PATH" ]; then
    echo "❌ Error: CSV file not found: $CSV_PATH"
    echo ""
    echo "Usage:"
    echo "  ./scripts/run_pipeline.sh [csv_path] [options]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/run_pipeline.sh"
    echo "  ./scripts/run_pipeline.sh data/companies.csv"
    echo "  ./scripts/run_pipeline.sh data/companies.csv --dry-run"
    echo "  ./scripts/run_pipeline.sh data/companies.csv --max-companies 2"
    exit 1
fi

echo ""
echo "Pipeline Configuration:"
echo "  CSV Path: $CSV_PATH"
echo "  Additional Args: ${@:2}"
echo ""
echo "========================================"
echo ""

# Run the pipeline
python -m src.pipeline "$CSV_PATH" "${@:2}"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✅ Pipeline completed successfully!"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo "  • View data in database"
    echo "  • Start API server: ./scripts/run_api.sh"
    echo "  • Query API: curl http://localhost:8000/companies"
else
    echo ""
    echo "========================================"
    echo "❌ Pipeline failed with exit code: $EXIT_CODE"
    echo "========================================"
fi

exit $EXIT_CODE
