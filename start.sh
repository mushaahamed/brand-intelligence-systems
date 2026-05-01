#!/usr/bin/env bash
# Quick start script
set -e

echo "  ◈  BrandScope — Starting up..."
echo ""

# Check .env
if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "  [!] Created .env from .env.example — please fill in your API keys, then re-run."
  exit 1
fi

# Install deps
echo "  [→] Installing dependencies..."
pip install -r requirements.txt -q

# Run tests
echo "  [→] Running API tests..."
python -m pytest tests/test_apis.py::TestConfig tests/test_apis.py::TestHelpers tests/test_apis.py::TestPipelineBase -v --tb=short

# Start server
echo ""
echo "  [✓] Starting FastAPI server at http://localhost:8000 ..."
echo "  [✓] Open http://localhost:8000 in your browser"
echo ""
uvicorn api.main:app --reload --port 8000
