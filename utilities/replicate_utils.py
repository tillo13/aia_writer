"""All Replicate functionality"""
import replicate
from .google_secret_utils import get_secret

MODELS = {
    "gpt-5-nano": {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano", "description": "Fastest & cheapest", "pricing": {"input": 0.05, "output": 0.40}},
    "gpt-oss-120b": {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B", "description": "Best value", "pricing": {"input": 0.18, "output": 0.72}},
    "gpt-4o-mini": {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast", "pricing": {"input": 0.15, "output": 0.60}},
    "gpt-5-mini": {"id": "openai/gpt-5-mini", "name": "GPT-5 Mini", "description": "Balanced", "pricing": {"input": 0.25, "output": 2.00}},
    "gemini-2.5-flash": {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "Google fast", "pricing": {"input": 2.50, "output": 2.50}},
    "gpt-5": {"id": "openai/gpt-5", "name": "GPT-5", "description": "Excellent", "pricing": {"input": 1.25, "output": 10.00}},
    "claude-4.5-sonnet": {"id": "anthropic/claude-4.5-sonnet", "name": "Claude 4.5 Sonnet (Replicate)", "description": "Claude via Replicate - speed test", "pricing": {"input": 3.00, "output": 15.00}}
}

def get_client():
    return replicate.Client(api_token=get_secret('KUMORI_REPLICATE_API_KEY'))

def generate(model_key, prompt, max_tokens=2048):
    """Returns (success, text, cost)"""
    if model_key not in MODELS:
        return False, f"Unknown model: {model_key}", 0.0
    
    client = get_client()
    if not client:
        return False, "No client", 0.0
    
    try:
        output = client.run(MODELS[model_key]["id"], input={"prompt": prompt, "temperature": 0.7, "max_tokens": max_tokens})
        text = ''.join(str(x) for x in output) if hasattr(output, '__iter__') and not isinstance(output, str) else str(output)
        text = text.strip()
        
        pricing = MODELS[model_key]["pricing"]
        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4
        cost = (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
        
        return True, text, cost
    except Exception as e:
        return False, str(e), 0.0

def get_models():
    return [{"key": k, "name": v["name"], "description": v["description"]} for k, v in MODELS.items()]