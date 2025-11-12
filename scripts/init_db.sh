#!/bin/bash
# Database initialization script for CommonForge

set -e  # Exit on error

echo "🔧 Initializing CommonForge database..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "   Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Extract database name from DATABASE_URL
DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo "📦 Database: $DB_NAME"

# Check if PostgreSQL is running
if ! pg_isready > /dev/null 2>&1; then
    echo "❌ Error: PostgreSQL is not running"
    echo "   Start PostgreSQL and try again"
    exit 1
fi

echo "✓ PostgreSQL is running"

# Create database if it doesn't exist
if ! psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "📦 Creating database: $DB_NAME"
    createdb $DB_NAME
    echo "✓ Database created"
else
    echo "✓ Database already exists"
fi

# Initialize tables using Python
echo "📊 Creating database tables..."
python -m src.db

echo "✅ Database initialization complete!"
