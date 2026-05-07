#!/bin/bash
set -e

echo "=== Installing system dependencies ==="
sudo apt-get update -q
sudo apt-get install -y -q \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    poppler-utils

echo "=== Installing Python packages ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Creating output directory ==="
mkdir -p output

echo ""
echo "✅ Setup complete!"
echo "   → Add your GEMINI_API_KEY to .env"
echo "   → Run:  uvicorn app.main:app --reload --port 8000"
