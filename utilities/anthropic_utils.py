import json,re,base64
from anthropic import Anthropic
from .google_secret_utils import get_secret

client = None
def get_client():
    global client
    if not client: client = Anthropic(api_key=get_secret('KUMORI_ANTHROPIC_API_KEY'))
    return client

def search_sources(topic):
    """Search for 3 articles on topic, return list of {title, url, summary}"""
    r = get_client().messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"""Search for 3 recent news articles about: {topic}

Return ONLY valid JSON array, no other text:
[{{"title": "...", "url": "https://...", "summary": "2-3 sentence summary"}}]

Only include articles with real URLs. If you can't find 3, return fewer."""}])

    text = ''.join(b.text for b in r.content if hasattr(b, 'text'))
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match: return []
    try:
        sources = json.loads(match.group())
        return [s for s in sources if s.get('url', '').startswith('http')]
    except: return []

def analyze_style(files=None, sample_content=None):
    """Analyze writing style from uploaded files or sample content"""
    content = []

    if sample_content:
        content.append({"type": "text", "text": f"<doc name='sample.txt'>\n{sample_content}\n</doc>"})
    elif files:
        for f in files:
            data = f.read()
            ext = f.filename.split('.')[-1].lower()
            if ext == 'pdf':
                content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(data).decode()}})
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                mt = f"image/{'jpeg' if ext == 'jpg' else ext}"
                content.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": base64.b64encode(data).decode()}})
            else:
                content.append({"type": "text", "text": f"<doc name='{f.filename}'>\n{data.decode('utf-8', errors='ignore')}\n</doc>"})
    else:
        return "Write in a professional, engaging tone with clear structure."

    content.append({"type": "text", "text": """You are a world-class ghostwriter. Analyze these writing samples to deeply understand this author's voice.

Extract the ESSENCE of how they think and communicate:

1. MINDSET & PERSPECTIVE
   - How do they approach problems? (skeptical? enthusiastic? analytical?)
   - What's their relationship with the reader? (peer? mentor? fellow learner?)
   - What do they value? (practicality? honesty? experimentation?)

2. RHYTHM & FLOW
   - Sentence length patterns (do they vary? how?)
   - How do they transition between ideas?
   - Pacing - when do they speed up or slow down?

3. DISTINCTIVE MOVES
   - How do they hook readers at the start?
   - What makes their explanations land?
   - How do they handle complexity?
   - Their approach to evidence and examples

4. VOICE FINGERPRINTS
   - Characteristic phrases (but note: these should be used sparingly, not in every piece)
   - Tone markers - humor, directness, self-deprecation?
   - What they explicitly avoid

Output a style guide that captures the SPIRIT of this writer, not just surface patterns. A good ghostwriter channels the author's thinking, not just their verbal tics."""})

    r = get_client().messages.create(model="claude-sonnet-4-20250514", max_tokens=1500, messages=[{"role": "user", "content": content}])
    return r.content[0].text

ARTICLE_ANGLES = [
    "Lead with the most surprising or counterintuitive insight. Challenge conventional thinking.",
    "Start with a concrete scenario or problem the reader might face. Make it immediately relevant.",
    "Open with your honest reaction - what made you stop and think? Be genuinely reflective."
]

def generate_single_article(source, style, index):
    """Generate a single article for one source"""
    angle = ARTICLE_ANGLES[index % len(ARTICLE_ANGLES)]

    r = get_client().messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1500,
        messages=[{"role": "user", "content": f"""You are ghostwriting a LinkedIn post for a specific author. Your job is to channel their THINKING and PERSPECTIVE, not just mimic their phrases.

ARTICLE TO WRITE ABOUT:
Title: {source['title']}
URL: {source['url']}
Summary: {source['summary']}

THE AUTHOR'S VOICE (channel the spirit, not just the words):
{style}

YOUR ANGLE FOR THIS PIECE:
{angle}

GUIDELINES:
- 150-300 words
- Write as this person THINKS, not just how they phrase things
- Bring genuine insight - what would THIS author notice that others miss?
- Vary your structure - don't use the same opening/closing patterns every time
- Include the source URL naturally
- Avoid formulaic patterns like always starting with "TLDR:" or always ending with a question
- Make it feel like a real person wrote this specific post about this specific topic

The goal: if the author read this, they'd think "I wish I'd written that" - not "that sounds like a template."

Output ONLY the post text."""}])

    return {"content": r.content[0].text, "source": source}
