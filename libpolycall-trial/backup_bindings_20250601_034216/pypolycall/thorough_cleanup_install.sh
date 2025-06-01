#!/bin/bash

# Thorough PyPolyCall Cleanup and Installation Script
# Removes ALL cache files, egg-info, and pip cache before clean install

set -e

echo "🧹 THOROUGH PyPolyCall Cleanup and Installation"
echo "=============================================="

# Go to package directory
cd pypolycall

echo "🗑️  STEP 1: Removing ALL Python cache recursively..."

# Remove all __pycache__ directories recursively
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove all build artifacts
rm -rf *.egg-info/ 2>/dev/null || true
rm -rf .eggs/ 2>/dev/null || true
rm -rf build/ 2>/dev/null || true
rm -rf dist/ 2>/dev/null || true
rm -rf .pytest_cache/ 2>/dev/null || true
rm -rf .coverage 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true

echo "🗑️  STEP 2: Clearing pip cache..."

# Clear pip cache completely
pip cache purge 2>/dev/null || true

echo "🗑️  STEP 3: Removing temporary egg-info from /tmp/..."

# Remove any pypolycall-related temp files
sudo rm -rf /tmp/pip-pip-egg-info-* 2>/dev/null || true
sudo rm -rf /tmp/pip-* 2>/dev/null || true

# Also check user temp directories
rm -rf ~/.cache/pip/* 2>/dev/null || true

echo "🗑️  STEP 4: Final verification - no artifacts remain..."

# Verify no artifacts remain
echo "📊 Checking for remaining artifacts:"
echo "   __pycache__ directories: $(find . -name "__pycache__" | wc -l)"
echo "   .egg-info directories: $(find . -name "*.egg-info" | wc -l)"
echo "   .pyc files: $(find . -name "*.pyc" | wc -l)"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📦 STEP 5: Installing PyPolyCall with force reinstall..."

# Install with force reinstall and no cache
pip install -e . --force-reinstall --no-cache-dir --no-deps

if [[ $? -eq 0 ]]; then
    echo ""
    echo "🎉 PyPolyCall installation SUCCESSFUL!"
    echo "====================================="
    echo ""
    echo "🐍 Package: pypolycall"
    echo "📡 Port mapping: 3001:8084 (RESERVED FOR PYTHON)"
    echo "🛡️  Zero-trust: Enabled"
    echo ""
    echo "✅ Testing import..."
    python -c "import pypolycall; print('✅ PyPolyCall imported successfully')"
    
    echo ""
    echo "🚀 Ready to use:"
    echo "   1. Configure: sudo cp python.polycallrc /opt/polycall/services/python/"
    echo "   2. Test: python tests/test_router.py"
    echo "   3. Start: python examples/server.py"
    
else
    echo ""
    echo "❌ Installation still failed"
    echo "🔍 Checking setup.py content..."
    head -5 setup.py
    echo ""
    echo "📁 Current directory contents:"
    ls -la
fi
