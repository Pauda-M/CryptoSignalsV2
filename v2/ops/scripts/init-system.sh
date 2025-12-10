#!/bin/bash
#
# init-system.sh - Initialize CryptoTrader V2 on Linux
# Works on Ubuntu, Debian, CentOS, etc.
#
# Usage:
#   chmod +x ops/scripts/init-system.sh
#   ./ops/scripts/init-system.sh
#

set -e

echo "=========================================="
echo "CryptoTrader V2 - System Initialization"
echo "=========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo "✓ Detected OS: $OS"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi
NODE_VERSION=$(node -v)
echo "✓ Node.js: $NODE_VERSION"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✓ Python: $PYTHON_VERSION"

# Check PostgreSQL client
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found. You'll need it for database operations."
fi

echo ""
echo "========== Installing Dependencies =========="

# Create .env from .env.example if not exists
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Edit .env with your database connection string"
fi

# Install root dependencies
echo "📦 Installing root dependencies..."
if [ -f "package.json" ]; then
    npm install
fi

# Install service dependencies
echo "📦 Installing service dependencies..."
for service in services/*/; do
    if [ -f "$service/package.json" ]; then
        echo "  Installing $service..."
        cd "$service"
        npm install
        cd ../../
    fi
done

# Install dashboard dependencies
echo "📦 Installing dashboard dependencies..."
for dashboard in dashboards/*/; do
    if [ -f "$dashboard/package.json" ]; then
        echo "  Installing $dashboard..."
        cd "$dashboard"
        npm install
        cd ../../
    fi
done

# Create Python virtual environment
echo "📦 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv and install ML dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
if [ -f "ml/requirements.txt" ]; then
    pip install -r ml/requirements.txt
fi
deactivate

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p logs
mkdir -p data
mkdir -p ml/models
mkdir -p backups

# Set permissions
echo "🔐 Setting permissions..."
chmod +x ops/scripts/*.sh

echo ""
echo "========== System Initialized =========="
echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your database connection string"
echo "  2. Run: ./ops/scripts/db-init.sh (to initialize database)"
echo "  3. Run: ./ops/scripts/start-all.sh (to start all services)"
echo ""
