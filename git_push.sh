#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MAX_RETRIES=3
RETRY_DELAY=5

print_color() {
    echo -e "${1}${2}${NC}"
}

retry_push() {
    local attempt=1
    local delay=$RETRY_DELAY
    
    while [ $attempt -le $MAX_RETRIES ]; do
        print_color $BLUE "🔄 Push attempt $attempt of $MAX_RETRIES..."
        
        case $attempt in
            1)
                git push origin main
                ;;
            2)
                print_color $YELLOW "⚡ Trying with compression..."
                git config http.postBuffer 52428800
                git push origin main
                ;;
            3)
                print_color $YELLOW "🎯 Final attempt..."
                git config core.compression 9
                git push origin main
                ;;
        esac
        
        if [ $? -eq 0 ]; then
            print_color $GREEN "✅ Push successful!"
            return 0
        fi
        
        if [ $attempt -lt $MAX_RETRIES ]; then
            sleep $delay
            delay=$((delay * 2))
        fi
        
        attempt=$((attempt + 1))
    done
    
    return 1
}

if [ -z "$1" ]; then
    print_color $RED "❌ You must provide a commit message"
    echo "Usage: ./git_push.sh \"Your commit message\""
    exit 1
fi

if [ ! -d ".git" ]; then
    print_color $BLUE "🔧 Initializing git..."
    git init
    git branch -M main
    git remote add origin https://github.com/tillo13/aia_writer.git
fi

print_color $BLUE "📦 Adding changes..."
git add .

print_color $BLUE "💾 Committing..."
git commit -m "$1"

print_color $BLUE "🚀 Pushing to GitHub..."
retry_push

if [ $? -ne 0 ]; then
    print_color $RED "❌ Push failed after $MAX_RETRIES attempts"
    exit 1
fi

print_color $GREEN "✅ Git push completed!"

EXPECTED_PROJECT="aia-writer-2025"
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)

if [ "$CURRENT_PROJECT" != "$EXPECTED_PROJECT" ]; then
    print_color $YELLOW "⚠️  Switching to $EXPECTED_PROJECT..."
    gcloud config set project $EXPECTED_PROJECT
fi

echo ""
print_color $BLUE "🚀 Starting deployment..."
python3 gcloud_deploy.py

if [ $? -eq 0 ]; then
    print_color $GREEN "🎉 Deployment complete!"
else
    print_color $RED "❌ Deployment failed"
    exit 1
fi