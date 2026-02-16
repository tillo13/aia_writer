# Me-ish - AI-Powered Writing Style Cloning

**Live at:** [meish.cc](https://meish.cc)

An AI-powered content generation tool that analyzes your writing samples and creates articles in your authentic voice. Upload your work, choose a topic, and get publication-ready content that sounds like you.

---

## What It Does

**meish.cc** solves a real problem: how do you scale content creation without losing your unique voice?

Instead of generic AI-generated content, AIA:
1. **Analyzes your writing style** - Extracts your mindset, rhythm, distinctive patterns, and voice fingerprints
2. **Finds relevant sources** - Searches for recent news articles on your chosen topic
3. **Generates authentic content** - Creates multiple article drafts that match your thinking and communication style

**Free, private, no signup required.** Nothing is saved. Your writing samples and generated content exist only during your session.

---

## Key Features

### 🎯 Deep Style Analysis
- Analyzes mindset and perspective (how you approach problems)
- Captures rhythm and flow (sentence patterns, pacing, transitions)
- Identifies distinctive moves (how you hook readers, explain complexity)
- Extracts voice fingerprints (characteristic phrases, tone markers)

### 🔍 Real-Time Source Discovery
- Searches for recent, relevant news articles on any topic
- Uses Claude's web search capabilities for current information
- Validates sources and filters for quality

### ✍️ Authentic Content Generation
- Generates 150-300 word articles in your voice
- Varies angles and approaches (counterintuitive insights, concrete scenarios, honest reactions)
- Includes source attribution naturally
- Avoids formulaic patterns and template-like writing

### ⚡ Server-Sent Events (SSE) Streaming
- Real-time progress updates during generation
- Streams articles as they're created
- Responsive UI with live status messages

### 🛡️ Content Filtering
- Automatic profanity and inappropriate content detection
- Uses Shutterstock's LDNOOBW word list
- Customizable blocked words via environment variables

---

## Tech Stack

**Backend:**
- Python 3.12
- Flask web framework
- Anthropic Claude Sonnet 4 for AI analysis and generation
- Google Cloud Secret Manager for secure credential storage

**Frontend:**
- Vanilla JavaScript with Server-Sent Events
- Responsive CSS with modern gradient UI
- Progressive disclosure design patterns

**Infrastructure:**
- Google Cloud Platform (App Engine)
- Custom domain with SSL (meish.cc)
- Auto-scaling F2 instances
- Gunicorn production server

---

## How It Works

### 1. Style Analysis

Upload writing samples (PDFs, text files, images with text) or use the sample style. Claude Sonnet 4 analyzes:
- **Mindset & Perspective:** How you approach problems, your relationship with readers, what you value
- **Rhythm & Flow:** Sentence length patterns, transitions, pacing
- **Distinctive Moves:** Opening hooks, explanations, handling complexity
- **Voice Fingerprints:** Characteristic phrases, tone markers, what you avoid

The system extracts the **spirit** of your writing, not just surface patterns.

### 2. Source Discovery

Enter any topic. The system:
- Uses Claude's web search tool to find 3 recent, relevant articles
- Validates URLs and filters for quality
- Returns title, URL, and summary for each source

### 3. Article Generation

For each source, Claude generates a unique article:
- **Varied angles:** Counterintuitive insights, concrete scenarios, honest reactions
- **Length:** 150-300 words (LinkedIn-optimized)
- **Authenticity:** Channels your thinking, not just your phrases
- **Source integration:** Includes URLs naturally in the text

Each article uses a different structural approach to avoid repetitive patterns.

---

## Architecture Highlights

### Secure Credential Management

```python
from google.cloud import secretmanager

def get_secret(name, project='kumori-404602'):
    client = secretmanager.SecretManagerServiceClient()
    return client.access_secret_version(
        request={"name": f"projects/{project}/secrets/{name}/versions/latest"}
    ).payload.data.decode('UTF-8')
```

API keys stored in Google Cloud Secret Manager, never hardcoded or committed to git.

### Real-Time Streaming

```python
def generate_stream():
    yield f"data: {json.dumps({'type': 'status', 'message': 'Searching...'})}\n\n"
    sources = search_sources(topic)
    yield f"data: {json.dumps({'type': 'sources', 'count': len(sources)})}\n\n"

    for i, src in enumerate(sources):
        article = generate_single_article(src, style, i)
        yield f"data: {json.dumps({'type': 'article', 'article': article})}\n\n"
```

Server-Sent Events provide real-time progress updates without polling.

### Content Safety

```python
def check_content_filter(message):
    blocked_phrases = get_blocked_words()  # LDNOOBW + custom
    message_lower = message.lower()

    for phrase in blocked_phrases:
        if phrase in message_lower:
            return False, "Please keep your topic professional."

    return True, None
```

Automatic content filtering prevents misuse while maintaining user experience.

---

## Project Structure

```
aia/
├── app.py                          # Flask application with SSE streaming
├── app.yaml                        # GCP App Engine configuration
├── requirements.txt                # Python dependencies
├── utilities/
│   ├── anthropic_utils.py         # Claude API integration
│   ├── content_filter.py          # Profanity and safety filtering
│   └── google_secret_utils.py     # Secret Manager integration
├── templates/
│   └── index.html                 # Main application interface
└── static/
    ├── style.css                  # Modern gradient UI
    └── app.js                     # SSE client and interactions
```

---

## Key Design Decisions

### Why Claude Sonnet 4?

- **Style analysis requires nuance:** Sonnet 4 excels at understanding writing patterns and extracting the "spirit" of a voice
- **Web search integration:** Native web search tool for current, relevant sources
- **Quality over speed:** Willing to spend 3-5 seconds per article for authentic output

### Why No Database?

- **Privacy-first:** Nothing is saved. Your samples and content are session-only.
- **Stateless design:** Each request is independent, no user tracking
- **Simplicity:** No data management, no cleanup, no retention policies

### Why Server-Sent Events?

- **Better UX:** Users see progress in real-time, not just a spinner
- **Simpler than WebSockets:** Unidirectional streaming is all we need
- **Native browser support:** No special libraries required

---

## Usage Examples

### Basic Flow

1. Visit [meish.cc](https://meish.cc)
2. Upload 1-3 writing samples (or use sample style)
3. Enter a topic (e.g., "AI agents in healthcare")
4. Watch as AIA:
   - Analyzes your style
   - Finds relevant sources
   - Generates 3 articles in your voice
5. Copy and use the articles you like

### Sample Topics

- Technical: "Enterprise AI implementation challenges"
- Industry: "Future of autonomous vehicles"
- Business: "Remote work productivity trends"
- Science: "CRISPR gene editing advances"

---

## What I Learned

### AI Engineering

- Prompt engineering for style analysis (extracting essence vs. surface patterns)
- Balancing authenticity with variety (avoiding template-like outputs)
- Using AI tools (web search) within generation workflows
- Iterative refinement of generation prompts based on output quality

### Full-Stack Integration

- Server-Sent Events for real-time streaming
- Flask production patterns with Gunicorn
- Google Cloud Secret Manager integration
- Content filtering for production safety

### Product Design

- Privacy-first architecture (no data persistence)
- Progressive disclosure UI patterns
- Real-time feedback for long-running operations
- Balancing simplicity with capability

---

## Deployment

Deployed on Google Cloud Platform App Engine with:
- Python 3.12 runtime
- F2 instance class
- Auto-scaling (0-2 instances)
- Custom domain (meish.cc) with SSL
- Gunicorn production server (1 worker, 4 threads, 300s timeout)

---

## Security & Privacy

**What's Protected:**
- API keys stored in Secret Manager, never in code
- No user data collected or stored
- Content filtering prevents abuse
- HTTPS-only with automatic redirects

**What's Transparent:**
- Open-source codebase (you're reading it!)
- Clear about AI usage (Claude Sonnet 4)
- Source attribution in generated content

---

## Future Improvements

Potential enhancements (not currently implemented):

- **Multi-language support:** Analyze and generate in languages beyond English
- **Tone adjustment:** Dial up/down formality, enthusiasm, technical depth
- **Export formats:** Download as Markdown, HTML, or plain text
- **Batch generation:** Process multiple topics at once
- **Style library:** Save and reuse analyzed styles (with user permission)

---

## Try It Live

**Visit:** [meish.cc](https://meish.cc)

See the power of AI-driven writing style cloning in action. Upload your samples, choose a topic, and get authentic content in seconds.

---

## License

This is a portfolio project demonstrating AI integration, Flask development, and production deployment patterns. Feel free to explore the code and concepts.

---

**Built to solve real content creation challenges while maintaining authentic voice.** 🎯
