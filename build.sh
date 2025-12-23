#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- 🚀 STARTING BUILD SCRIPT ---"

echo "--- 📦 Building Frontend ---"
cd frontend
npm install
npm run build
echo "--- ✅ Frontend Build Complete ---"

# Debug: Show us what we built
echo "--- 🔍 Checking frontend/dist ---"
if [ -d "dist" ]; then
    ls -la dist
else
    echo "❌ ERROR: frontend/dist directory missing!"
    exit 1
fi

echo "--- 🐍 Building Backend Dependencies ---"
cd ../backend
pip install -r requirements.txt

echo "--- 📂 Preparing Static Files ---"
# Remove old build if exists
rm -rf dist_build
mkdir -p dist_build

# Copy files
echo "Copying from ../frontend/dist to dist_build..."
if cp -r ../frontend/dist/* dist_build/; then
    echo "✅ Copy successful"
else
    echo "❌ Copy failed"
    exit 1
fi

echo "--- 🔍 Verifying backend/dist_build ---"
ls -la dist_build

echo "--- 🎉 BUILD COMPLETE ---"
