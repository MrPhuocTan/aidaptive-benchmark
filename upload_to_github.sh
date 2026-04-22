#!/bin/bash

# Script to automate pushing code to GitHub

# 1. Initialize Git if not already done
if [ ! -d ".git" ]; then
    echo "Initializing Git repository..."
    git init
    git branch -M main
fi

# 2. Check for remote origin
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ -z "$REMOTE_URL" ]; then
    echo "Enter your GitHub Repository URL (e.g., https://github.com/username/repo.git):"
    read REPO_URL
    if [ -z "$REPO_URL" ]; then
        echo "Error: Repository URL is required."
        exit 1
    fi
    git remote add origin "$REPO_URL"
fi

# 3. Add and Commit
echo "Staging files..."
git add .

echo "Enter commit message (default: 'Update benchmark suite'):"
read COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Update benchmark suite"
fi

git commit -m "$COMMIT_MSG"

# 4. Push
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "Successfully uploaded to GitHub!"
else
    echo "Failed to upload. Please check your credentials and URL."
fi
