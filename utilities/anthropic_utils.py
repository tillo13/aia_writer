import json,re,base64,logging,time,os,requests as _requests
import psycopg2
from .google_secret_utils import get_secret

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
_api_key = None

def _get_headers():
    global _api_key
    if not _api_key: _api_key = get_secret('KUMORI_ANTHROPIC_API_KEY')
    return {'x-api-key': _api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'}

# --- API usage tracking ---
APP_NAME = 'aia'
_PRICING = {
    'haiku-4-5': {'input': 0.0000008, 'output': 0.000004},   # $0.80/$4 per million
    'sonnet-4-5': {'input': 0.000003, 'output': 0.000015},   # $3/$15 per million
    'sonnet-4': {'input': 0.000003, 'output': 0.000015},     # $3/$15 per million
    'opus-4-6': {'input': 0.000015, 'output': 0.000075},     # $15/$75 per million
    'opus-4-5': {'input': 0.000015, 'output': 0.000075},     # $15/$75 per million
}

def _get_pricing(model):
    m = model.lower()
    for k, v in _PRICING.items():
        if k in m: return v
    return {'input': 0.000003, 'output': 0.000015}

def log_api_usage(model, usage, feature=None, streaming=False,
                  image_count=0, user_id=None, duration_ms=None):
    """Log an API call to kumori_api_usage in a background thread.
    Never blocks the caller. Never raises."""
    import threading

    def _do_log():
        try:
            pricing = _get_pricing(model)
            input_tokens = usage.get('input_tokens', 0) if isinstance(usage, dict) else 0
            output_tokens = usage.get('output_tokens', 0) if isinstance(usage, dict) else 0
            cache_creation = usage.get('cache_creation_input_tokens', 0) if isinstance(usage, dict) else 0
            cache_read = usage.get('cache_read_input_tokens', 0) if isinstance(usage, dict) else 0
            thinking = usage.get('thinking_tokens', 0) if isinstance(usage, dict) else 0
            server_tools = usage.get('server_tool_use') if isinstance(usage, dict) else None
            server_tools = server_tools or {}
            web_searches = server_tools.get('web_search_requests', 0) if isinstance(server_tools, dict) else 0
            web_fetches = server_tools.get('web_fetch_requests', 0) if isinstance(server_tools, dict) else 0
            code_exec = server_tools.get('code_execution_requests', 0) if isinstance(server_tools, dict) else 0
            cost = (input_tokens * pricing['input'] + output_tokens * pricing['output']
                    + cache_creation * pricing['input'] * 1.25 + cache_read * pricing['input'] * 0.1
                    + thinking * pricing['output'] + web_searches * 0.01)
            is_gcp = os.environ.get('GAE_ENV', '').startswith('standard')
            host = f"/cloudsql/{get_secret('KUMORI_POSTGRES_CONNECTION_NAME')}" if is_gcp else get_secret('KUMORI_POSTGRES_IP')
            conn = psycopg2.connect(host=host,
                database=get_secret('KUMORI_POSTGRES_DB_NAME'),
                user=get_secret('KUMORI_POSTGRES_USERNAME'),
                password=get_secret('KUMORI_POSTGRES_PASSWORD'),
                connect_timeout=5)
            try:
                cur = conn.cursor()
                cur.execute("""INSERT INTO kumori_api_usage
                    (app_name, feature, model, input_tokens, output_tokens,
                     cache_creation_tokens, cache_read_tokens, thinking_tokens,
                     web_search_requests, web_fetch_requests, code_execution_requests,
                     image_count, estimated_cost_usd, streaming, user_id, duration_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (APP_NAME, feature, model, input_tokens, output_tokens,
                     cache_creation, cache_read, thinking, web_searches, web_fetches,
                     code_exec, image_count, cost, streaming, user_id, duration_ms))
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to log API usage: {e}")

    threading.Thread(target=_do_log, daemon=True).start()

def _call_claude(body, timeout=60, user_id=None):
    start = time.time()
    r = _requests.post(API_URL, headers=_get_headers(), json=body, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    elapsed_ms = int((time.time() - start) * 1000)
    if 'usage' in data:
        feature = 'search' if body.get('tools') else 'generate'
        image_count = sum(1 for m in body.get('messages', [])
                         for c in (m.get('content', []) if isinstance(m.get('content'), list) else [])
                         if isinstance(c, dict) and c.get('type') in ('image', 'document'))
        log_api_usage(body.get('model', 'unknown'), data['usage'],
                      feature=feature, image_count=image_count, duration_ms=elapsed_ms,
                      user_id=user_id or 'system:aia')
    return data

def search_sources(topic):
    """Search for 3 articles on topic, return list of {title, url, summary}"""
    data = _call_claude({
        'model': "claude-sonnet-4-20250514", 'max_tokens': 2000,
        'tools': [{"type": "web_search_20250305", "name": "web_search"}],
        'messages': [{"role": "user", "content": f"""Search for 3 recent news articles about: {topic}

Return ONLY valid JSON array, no other text:
[{{"title": "...", "url": "https://...", "summary": "2-3 sentence summary"}}]

Only include articles with real URLs. If you can't find 3, return fewer."""}]})

    text = ''.join(b['text'] for b in data['content'] if b.get('type') == 'text')
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match: return []
    try:
        sources = json.loads(match.group())
        return [s for s in sources if s.get('url', '').startswith('http')]
    except: return []

def analyze_style(file_contents=None, sample_content=None):
    """Analyze writing style from file contents or sample content

    file_contents: list of dicts with 'filename' and 'data' (bytes)
    sample_content: string of sample text
    """
    content = []

    if sample_content:
        content.append({"type": "text", "text": f"<doc name='sample.txt'>\n{sample_content}\n</doc>"})
    elif file_contents:
        for f in file_contents:
            data = f['data']
            filename = f['filename']
            ext = filename.split('.')[-1].lower()
            if ext == 'pdf':
                content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(data).decode()}})
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                mt = f"image/{'jpeg' if ext == 'jpg' else ext}"
                content.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": base64.b64encode(data).decode()}})
            else:
                content.append({"type": "text", "text": f"<doc name='{filename}'>\n{data.decode('utf-8', errors='ignore')}\n</doc>"})
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

    data = _call_claude({'model': "claude-sonnet-4-20250514", 'max_tokens': 1500, 'messages': [{"role": "user", "content": content}]})
    return data['content'][0]['text']

ARTICLE_ANGLES = [
    "Lead with the most surprising or counterintuitive insight. Challenge conventional thinking.",
    "Start with a concrete scenario or problem the reader might face. Make it immediately relevant.",
    "Open with your honest reaction - what made you stop and think? Be genuinely reflective."
]

def generate_single_article(source, style, index):
    """Generate a single article for one source"""
    angle = ARTICLE_ANGLES[index % len(ARTICLE_ANGLES)]

    data = _call_claude({
        'model': "claude-sonnet-4-20250514", 'max_tokens': 1500,
        'messages': [{"role": "user", "content": f"""You are ghostwriting a LinkedIn post for a specific author. Your job is to channel their THINKING and PERSPECTIVE, not just mimic their phrases.

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

Output ONLY the post text."""}]})

    return {"content": data['content'][0]['text'], "source": source}
