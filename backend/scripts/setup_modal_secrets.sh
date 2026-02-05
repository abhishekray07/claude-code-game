#!/bin/bash
# Setup Modal secrets for Claude Code Game

echo "Setting up Modal secrets..."
echo ""

# Prompt for values
read -p "Enter demo access code (leave blank to disable): " DEMO_ACCESS_CODE
read -p "Enter allowed origin (e.g., https://your-app.vercel.app): " ALLOWED_ORIGIN

# Create secret
modal secret create claude-game-secrets \
    DEMO_ACCESS_CODE="$DEMO_ACCESS_CODE" \
    ALLOWED_ORIGINS="$ALLOWED_ORIGIN,http://localhost:5173"

echo ""
echo "Modal secrets created successfully!"
echo ""
echo "To update secrets later, run:"
echo "  modal secret update claude-game-secrets KEY=VALUE"
