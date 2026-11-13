#!/bin/bash
set -e

echo "=== BreachBlog Daily Automated Publisher ==="
echo "Timestamp: $(date -u)"

# 1. Configure git credentials & identity
git config --global user.name "BreachModal Publisher"
git config --global user.email "fritz@robomodal.com"

# 2. Check required environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY is not set."
    exit 1
fi

# 3. Clone BreachLawAgency Next.js repository if GH_TOKEN is provided
if [ -n "$GH_TOKEN" ]; then
    echo "Configuring GitHub access with GH_TOKEN..."
    rm -rf /app/BreachLawAgency
    git clone "https://x-access-token:${GH_TOKEN}@github.com/FritzHeider/BreachLawAgency.git" /app/BreachLawAgency
    export NEXTJS_DIR=/app/BreachLawAgency
else
    echo "Warning: GH_TOKEN not set; BreachLawAgency repository integration will be skipped."
fi

# 4. Run daily publication script
echo "Running publish_trending.py..."
python publish_trending.py

# 5. Commit and push any new content in breachblog repo
if [ -n "$GH_TOKEN" ]; then
    echo "Pushing latest breachblog updates..."
    git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/FritzHeider/BreachBlog.git" || true
    git add content/ static/images/ || true
    if git status --porcelain | grep -q .; then
        git commit -m "Auto-publish daily content [$(date -u +'%Y-%m-%d')]" || true
        git push origin main || true
    else
        echo "No additional breachblog changes to commit."
    fi
fi

echo "=== BreachBlog Daily Publishing Complete ==="
