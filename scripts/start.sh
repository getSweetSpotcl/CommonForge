#!/bin/bash
#
# Start CommonForge Frontend + Backend
#
# This script starts the FastAPI server which serves both the API and the Vue.js frontend.
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  CommonForge - Starting Application${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "src/api/main.py" ]; then
    echo -e "${YELLOW}Error: Must run from CommonForge root directory${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Error: Virtual environment not found${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}✓${NC} Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Please create .env from .env.example and configure your credentials"
    exit 1
fi

# Check if frontend exists
if [ ! -f "frontend/index.html" ]; then
    echo -e "${YELLOW}Warning: Frontend not found at frontend/index.html${NC}"
    echo "Frontend will not be available"
fi

# Start the server
echo -e "${GREEN}✓${NC} Starting FastAPI server..."
echo ""
echo -e "${BLUE}Server will be available at:${NC}"
echo -e "  ${GREEN}•${NC} Frontend:   http://localhost:8000/app/"
echo -e "  ${GREEN}•${NC} API Docs:   http://localhost:8000/docs"
echo -e "  ${GREEN}•${NC} API Base:   http://localhost:8000"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run uvicorn
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
