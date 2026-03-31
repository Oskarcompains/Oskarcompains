#!/bin/bash
# ============================================================
# Polymarket Arb Bot — Startup script for Hostinger VPS
# ============================================================
# Usage: bash deploy/start.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

echo "✅ Starting server on port 8000..."
python3 server.py --host 0.0.0.0 --port 8000
