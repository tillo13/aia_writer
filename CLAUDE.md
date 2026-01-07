# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIA is a minimal Flask app that generates LinkedIn articles in your writing style. Pick a topic (or enter custom), upload writing samples, get 3 articles with source citations.

## Commands

```bash
pip install -r requirements.txt
python app.py                    # localhost:5000
python gcloud_deploy.py          # deploy to App Engine
```

## Architecture

```
app.py                      # Flask routes with SSE streaming
utilities/
  anthropic_utils.py        # Claude API: web search, style analysis, article generation
  google_secret_utils.py    # Secret Manager
templates/index.html        # Single page UI
static/app.js              # Frontend logic with SSE handling
static/style.css           # Styles
gcloud_deploy.py           # Deployment script with version management
```

## Flow

1. User enters topic + uploads writing samples (or uses sample style)
2. `/generate` endpoint streams via SSE:
   - `search_sources(topic)` finds 3 articles via Claude web search tool
   - `analyze_style(files)` extracts writing voice from samples
   - `generate_single_article()` creates articles one-by-one, streamed to frontend
3. Frontend displays articles progressively as they arrive

## API Keys

Google Secret Manager (project: `kumori-404602`):
- `KUMORI_ANTHROPIC_API_KEY`

## Deployment

App Engine project: `aia-writer-2025`
URL: https://aia-writer-2025.uc.r.appspot.com
