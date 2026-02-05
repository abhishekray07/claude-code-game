#!/bin/bash
# Deploy backend to Modal

set -e

echo "Deploying Claude Code Game backend to Modal..."
echo ""

cd "$(dirname "$0")/.."

# Deploy
modal deploy modal_app.py

echo ""
echo "Backend deployed successfully!"
echo ""
echo "Your backend URL will be shown above."
echo "Update your frontend VITE_API_URL with this URL."
