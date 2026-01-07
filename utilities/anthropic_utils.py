import json,re,base64,concurrent.futures
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
    """Analyze writing style from uploaded files or sample content, return style profile string"""
    content = []

    if sample_content:
        # Use provided sample content directly
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

    content.append({"type": "text", "text": """Analyze these writing samples. Extract the author's voice in 100 words or less:
- Tone and personality
- Sentence patterns (short? questions? casual?)
- Recurring phrases or verbal tics
- How they open/close pieces
- What they avoid

Be specific. Use examples from the text. Output as a concise style guide."""})

    r = get_client().messages.create(model="claude-sonnet-4-20250514", max_tokens=1000, messages=[{"role": "user", "content": content}])
    return r.content[0].text

def generate_articles(sources, style):
    """Generate one article per source in the user's style"""
    articles = []
    for src in sources:
        r = get_client().messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1500,
            messages=[{"role": "user", "content": f"""Write a LinkedIn post about this article in the specified writing style.

SOURCE:
Title: {src['title']}
URL: {src['url']}
Summary: {src['summary']}

WRITING STYLE TO MATCH:
{style}

Requirements:
- 150-250 words
- Match the voice/tone exactly
- Include your unique take, not just summary
- End with the source attribution

Output ONLY the post text, nothing else."""}])
        articles.append({"content": r.content[0].text, "source": src})
    return articles

def fetch_and_analyze(topic, files=None, sample_content=None):
    """Run source search and style analysis in parallel"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        sources_future = ex.submit(search_sources, topic)
        style_future = ex.submit(analyze_style, files, sample_content)
        return sources_future.result(), style_future.result()
