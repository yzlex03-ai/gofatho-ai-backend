#!/usr/bin/env bash
# One-command script to push the Gofatho AI repo to GitHub and trigger the Cloud APK & AAB build
set -e

REPO_URL="${1:-https://github.com/YOUR_USERNAME/gofatho-ai-mobile.git}"

echo "[1/4] Copying latest gofatho_ai_master.sqlite into flutter_app/assets/..."
cp -f data/gofatho_ai_master.sqlite flutter_app/assets/gofatho_ai_master.sqlite

echo "[2/4] Initializing Git repository..."
git init
git checkout -B main
git add .
git commit -m "Release v1.4.0: Gofatho AI Production Flutter Android App + Offline SQLite FTS5 + Cloud APK Builder" || true

echo "[3/4] Pushing to $REPO_URL..."
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git push -u origin main

echo "[4/4] Cloud APK & AAB Build triggered! Open your GitHub repository -> Actions tab to download Gofatho-AI-Android-APKs-v1.4.0.zip."
