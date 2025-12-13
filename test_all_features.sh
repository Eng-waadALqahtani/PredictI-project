#!/bin/bash

echo "========================================"
echo "  PredictAI - Feature Testing"
echo "========================================"
echo ""

cd "$(dirname "$0")"
python3 backend/test_features.py

