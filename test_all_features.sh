#!/bin/bash

echo "========================================"
echo "  PredictIQ - Feature Testing"
echo "========================================"
echo ""

cd "$(dirname "$0")"
python3 backend/test_features.py

