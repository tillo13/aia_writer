#!/usr/bin/env python3
"""
Replicate Model Tester
Tests multiple LLM models with a simple "hello world" prompt
Uses kumori secrets pattern from galactica game
Automatically switches to kumori project for secrets access
Tracks total cost spent on testing
"""

import replicate
from google.cloud import secretmanager
import subprocess
import sys

# Kumori secrets project (where all secrets live)
SECRETS_PROJECT_ID = "kumori-404602"
REPLICATE_SECRET_NAME = "KUMORI_REPLICATE_API_KEY"  # Actual secret name in kumori

# Model pricing (per 1M tokens) - based on 2025 pricing research
MODEL_PRICING = {
    "openai/gpt-5-nano": {"input": 0.05, "output": 0.40},
    "openai/gpt-oss-120b": {"input": 0.18, "output": 0.72},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-5-mini": {"input": 0.25, "output": 2.00},
    "google/gemini-2.5-flash": {"input": 2.50, "output": 2.50},  # Flat rate
    "openai/gpt-5": {"input": 1.25, "output": 10.00},
    "anthropic/claude-4.5-sonnet": {"input": 3.00, "output": 15.00},
}

def get_current_gcloud_project() -> str:
    """Get the currently active gcloud project"""
    try:
        result = subprocess.run(
            ['gcloud', 'config', 'get-value', 'project'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return None

def set_gcloud_project(project_id: str) -> bool:
    """Set the active gcloud project"""
    try:
        subprocess.run(
            ['gcloud', 'config', 'set', 'project', project_id],
            capture_output=True,
            check=True
        )
        return True
    except Exception:
        return False

def get_secret(secret_id: str, project_id: str = SECRETS_PROJECT_ID) -> str:
    """
    Get secret from Google Secret Manager
    Follows the galactica/kumori pattern
    Automatically switches projects if needed
    """
    # Save current project
    original_project = get_current_gcloud_project()
    print(f"📍 Current gcloud project: {original_project}")
    
    # Switch to secrets project if needed
    if original_project != project_id:
        print(f"🔄 Switching to secrets project: {project_id}")
        if not set_gcloud_project(project_id):
            print(f"⚠️  Could not switch to {project_id}, trying anyway...")
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        print(f"🔍 Fetching: {name}")
        
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode('UTF-8')
        print(f"✅ Retrieved secret: {secret_id}")
        
        # Restore original project
        if original_project and original_project != project_id:
            print(f"🔄 Restoring original project: {original_project}")
            set_gcloud_project(original_project)
        
        return secret_value
        
    except Exception as e:
        print(f"❌ Error getting secret {secret_id}: {e}")
        
        # Restore original project even on error
        if original_project and original_project != project_id:
            set_gcloud_project(original_project)
        
        return None

def count_tokens(text: str) -> int:
    """
    Rough token estimation: ~4 chars per token
    This is approximate but good enough for cost tracking
    """
    return len(text) // 4

def calculate_cost(model_name: str, input_text: str, output_text: str) -> float:
    """Calculate the cost of a single API call"""
    if model_name not in MODEL_PRICING:
        return 0.0
    
    pricing = MODEL_PRICING[model_name]
    input_tokens = count_tokens(input_text)
    output_tokens = count_tokens(output_text)
    
    # Cost = (tokens / 1M) * price_per_1M
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + output_cost

def test_model(client, model_name: str, prompt: str = "Say hello!"):
    """
    Test a single model with a simple prompt
    Returns (success, cost, response_text)
    """
    print(f"\n{'='*70}")
    print(f"🤖 Testing: {model_name}")
    print(f"{'='*70}")
    
    try:
        # Special handling for Claude - it requires higher max_tokens
        input_params = {
            "prompt": prompt,
            "temperature": 0.7
        }
        
        # Claude 4.5 Sonnet requires min 1024 tokens
        if "claude" in model_name.lower():
            input_params["max_tokens"] = 1024
        else:
            input_params["max_tokens"] = 100
        
        # Run the model using the client instance
        output = client.run(model_name, input=input_params)
        
        # Collect output (handle both string and generator responses)
        if hasattr(output, '__iter__') and not isinstance(output, str):
            response = ''.join(str(item) for item in output)
        else:
            response = str(output)
        
        response = response.strip()
        
        # Calculate cost
        cost = calculate_cost(model_name, prompt, response)
        
        print(f"📝 Response from {model_name}:")
        print(f"   {response[:100]}{'...' if len(response) > 100 else ''}")
        print(f"💰 Cost: ${cost:.8f} (${cost * 1000:.5f} per 1K calls)")
        print(f"✅ SUCCESS")
        
        return True, cost, response
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False, 0.0, ""

def main():
    """
    Test multiple models with hello world prompt
    """
    print("🚀 Replicate Model Tester")
    print("Using kumori secrets pattern from galactica game\n")
    
    # Get Replicate API token from kumori secrets
    print("🔑 Fetching Replicate API token from kumori secrets...")
    api_token = get_secret(REPLICATE_SECRET_NAME, SECRETS_PROJECT_ID)
    
    if not api_token:
        print(f"❌ Could not retrieve Replicate API token!")
        print(f"Make sure {REPLICATE_SECRET_NAME} exists in {SECRETS_PROJECT_ID} project")
        sys.exit(1)
    
    # Initialize Replicate client
    client = replicate.Client(api_token=api_token)
    print("✅ Replicate client initialized\n")
    
    # Models to test (from your pricing research)
    models_to_test = [
        # Cheapest models
        ("openai/gpt-5-nano", "GPT-5-nano (Cheapest - $0.05/$0.40)"),
        ("openai/gpt-oss-120b", "GPT-OSS-120B (Best Value - $0.18/$0.72)"),
        ("openai/gpt-4o-mini", "GPT-4o-mini (Fast - $0.15/$0.60)"),
        
        # Mid-tier quality
        ("openai/gpt-5-mini", "GPT-5-mini (Good Balance - $0.25/$2.00)"),
        ("google/gemini-2.5-flash", "Gemini 2.5 Flash (Flat Rate - $2.50/$2.50)"),
        
        # Premium models
        ("openai/gpt-5", "GPT-5 (Excellent - $1.25/$10.00)"),
        ("anthropic/claude-4.5-sonnet", "Claude 4.5 Sonnet (Best Quality - $3.00/$15.00)"),
    ]
    
    # Test prompt
    test_prompt = "Say hello and introduce yourself briefly!"
    
    # Track results
    results = {
        'passed': [],
        'failed': [],
        'costs': {}
    }
    total_cost = 0.0
    
    print(f"📋 Testing {len(models_to_test)} models with prompt:")
    print(f"   '{test_prompt}'\n")
    
    # Test each model
    for model_id, description in models_to_test:
        success, cost, response = test_model(client, model_id, test_prompt)
        
        if success:
            results['passed'].append(description)
            results['costs'][description] = cost
            total_cost += cost
        else:
            results['failed'].append(description)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"✅ Passed: {len(results['passed'])}/{len(models_to_test)}")
    print(f"❌ Failed: {len(results['failed'])}/{len(models_to_test)}")
    
    if results['passed']:
        print("\n✅ Working Models:")
        for model in results['passed']:
            cost = results['costs'].get(model, 0.0)
            print(f"   • {model}")
            print(f"     Cost: ${cost:.8f}")
    
    if results['failed']:
        print("\n❌ Failed Models:")
        for model in results['failed']:
            print(f"   • {model}")
    
    # Cost breakdown
    print("\n" + "="*70)
    print("💰 COST BREAKDOWN")
    print("="*70)
    print(f"Total spent on this test: ${total_cost:.8f}")
    print(f"Average cost per model: ${total_cost / len(results['passed']) if results['passed'] else 0:.8f}")
    
    if total_cost < 0.01:
        print(f"\n💡 That's less than {total_cost * 100:.4f} cents total!")
        print(f"   Or about {total_cost * 1000:.6f} cents per model test")
    else:
        print(f"\n💡 That's {total_cost * 100:.4f} cents total")
    
    print("\n✨ Testing complete!")

if __name__ == "__main__":
    main()