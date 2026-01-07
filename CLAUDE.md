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
app.py                      # Flask routes (~40 lines)
utilities/
  anthropic_utils.py        # Claude API: search, analyze, generate (~80 lines)
  google_secret_utils.py    # Secret Manager (~5 lines)
templates/index.html        # Single page UI
static/app.js              # Frontend logic (~70 lines)
static/style.css           # Dark theme
```

## Flow

1. User picks topic → `search_sources(topic)` finds 3 articles via Claude web search
2. User uploads samples → `analyze_style(files)` extracts writing voice
3. Both run in parallel via `fetch_and_analyze()`
4. `generate_articles(sources, style)` creates one article per source
5. Each article includes source URL for verification

## API Keys

Google Secret Manager (project: `kumori-404602`):
- `KUMORI_ANTHROPIC_API_KEY`

## Deployment

App Engine project: `aia-writer-2025`
URL: https://aia-writer-2025.uc.r.appspot.com
