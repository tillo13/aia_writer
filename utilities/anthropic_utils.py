"""All Anthropic/Claude functionality - optimized"""
import base64,concurrent.futures,re
from anthropic import Anthropic
from .google_secret_utils import get_secret

def get_client():
    return Anthropic(api_key=get_secret('KUMORI_ANTHROPIC_API_KEY'))

def strip_markdown_code_fence(text):
    """Remove markdown code fences (```json, ```, etc.) from text"""
    # Remove opening code fence (```json or ```)
    text = re.sub(r'^```(?:json)?\s*\n', '', text, flags=re.MULTILINE)
    # Remove closing code fence (```)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def fetch_news_only():
    """Just fetch news - fast and cacheable"""
    client=get_client()
    r=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=2000,
        tools=[{"type":"web_search_20250305","name":"web_search"}],
        messages=[{"role":"user","content":"Find the single biggest AI tech news story from today and summarize it in 3-4 paragraphs. Include what happened, why it matters, and key details."}])
    return ''.join(b.text for b in r.content if b.type=="text")

def analyze_style_only(files):
    """Just analyze style - returns JSON string"""
    client=get_client()
    content=[]
    
    for f in files:
        data=f.read()
        b64=base64.b64encode(data).decode('utf-8')
        ext=f.filename.split('.')[-1].lower()
        
        if ext=='pdf':
            content.append({"type":"document","source":{"type":"base64","media_type":"application/pdf","data":b64}})
        elif ext in['jpg','jpeg','png','gif','webp']:
            content.append({"type":"image","source":{"type":"base64","media_type":f"image/{ext if ext!='jpg'else'jpeg'}","data":b64}})
        else:
            text=data.decode('utf-8',errors='ignore')
            content.append({"type":"text","text":f"<document name='{f.filename}'>\n{text}\n</document>"})
    
    content.append({"type":"text","text":"""You are a writing style analyst. Analyze all provided documents to extract the author's complete writing DNA.

Extract and output a JSON object with this exact structure:

{
  "conversational_patterns": {
    "natural_voice_markers": ["phrases appearing 5+ times - their verbal tics and recurring language"],
    "opening_patterns": ["common first paragraph structures as templates with {placeholders}"],
    "transition_phrases": ["recurring connectors between ideas"],
    "closing_patterns": ["common ending structures as templates"]
  },
  
  "authenticity_markers": {
    "vulnerability_patterns": ["how they admit mistakes, share failures, show uncertainty"],
    "technical_authenticity": ["how they use real numbers, specs, metrics, timestamps, costs"],
    "what_they_never_fabricate": ["things they're always specific about vs vague"]
  },
  
  "style_fingerprints": {
    "sentence_patterns": ["typical structures - short? questions? compound?"],
    "paragraph_rhythm": "how they structure paragraphs",
    "tone": "their consistent voice quality",
    "technical_depth": "how deep they go with details"
  },
  
  "signature_elements": {
    "analogies": ["recurring metaphors or comparison styles"],
    "examples": ["types of examples they use"],
    "interaction_style": "how they address readers"
  },
  
  "anti_patterns": {
    "never_uses": ["words/phrases consistently absent"],
    "avoids": ["patterns they consciously avoid - hype, corporate speak, etc"]
  }
}

Rules:
- Only include patterns appearing in 3+ documents
- Use exact phrases from documents for voice_markers
- Create templates with {placeholders} for patterns
- Be specific, not generic
- Output ONLY valid JSON, no explanation"""})
    
    r=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=8000,messages=[{"role":"user","content":content}])
    raw_text = r.content[0].text
    # Strip markdown code fences if present
    return strip_markdown_code_fence(raw_text)

def analyze_style_and_fetch_news(files):
    """Run style analysis and news fetch IN PARALLEL"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        style_future=executor.submit(analyze_style_only,files)
        news_future=executor.submit(fetch_news_only)
        
        style_json=style_future.result()
        news=news_future.result()
    
    return style_json,news

def restyle_content(style_json,news_text,model_name="Claude Sonnet 4"):
    """Restyle content using Claude"""
    client=get_client()
    
    prompt=f"""You are a writing style adapter. You have been given:

1. A detailed JSON style profile of a writer
2. An AI news article (originally written by {model_name})

Your task: Rewrite the news article to match the writer's style perfectly.

STYLE PROFILE:
{style_json}

ORIGINAL NEWS ARTICLE:
{news_text}

Instructions:
- Apply ALL patterns from the style profile
- Match their conversational voice markers and recurring phrases
- Use their sentence structures and paragraph rhythm
- Incorporate their authenticity markers (how they use specifics, admit uncertainty, etc)
- Follow their opening and closing patterns
- Avoid their anti-patterns
- Keep the same factual content but transform the voice completely

Output ONLY the rewritten article, no explanations."""
    
    r=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=4000,messages=[{"role":"user","content":prompt}])
    return r.content[0].text

def stream_chat(model,messages,temperature,max_tokens,enable_web_search,enable_thinking):
    """Stream chat responses"""
    client=get_client()
    params={"model":model,"max_tokens":max_tokens,"temperature":temperature,"messages":messages}
    
    web_search_models=['claude-opus-4','claude-sonnet-4','claude-3-7-sonnet','claude-3-5-sonnet','claude-3-5-haiku']
    if enable_web_search and any(m in model for m in web_search_models):
        params["tools"]=[{"type":"web_search_20250305","name":"web_search"}]
    
    thinking_models=['claude-opus-4','claude-sonnet-4']
    if enable_thinking and any(m in model for m in thinking_models):
        params["thinking"]={"type":"enabled","budget_tokens":8000}
    
    with client.messages.stream(**params)as stream:
        for text in stream.text_stream:
            yield text