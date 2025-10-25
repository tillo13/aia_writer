#!/usr/bin/env python3
"""
Local Speed Test: Replicate Claude vs Direct Anthropic API
Tests both versions side-by-side with the same style profile and story
"""

import json
import time
import glob
import os
import random

# Import your utilities
from utilities.anthropic_utils import restyle_content
from utilities.replicate_utils import generate

# The style profile from your cover letter
STYLE_PROFILE = {
  "conversational_patterns": {
    "natural_voice_markers": ["I'm excited to", "What draws me most to", "I bring exactly what", "I embody the", "I'm also honest about", "I would love the opportunity to"],
    "opening_patterns": ["I'm excited to apply for the {position} at your {location}. As a {relationship_to_company}, I've always {positive_observation}—and I want to be part of {shared_goal}."],
    "transition_phrases": ["What draws me most to", "I bring exactly what", "I embody the traits you value:", "I'm also honest about", "I'm reliable and local:"],
    "closing_patterns": ["I would love the opportunity to bring my {qualities} to the {company} team. I'm confident I can help {specific_contribution}—{memorable_phrase}. Thank you for considering my application."]
  },
  
  "authenticity_markers": {
    "vulnerability_patterns": ["I'm also honest about what I don't know yet", "I'm eager to learn everything about"],
    "technical_authenticity": ["seven years of fostering over 200 animals", "consistent availability on Saturdays and Sundays", "available anytime for an interview and can start immediately"],
    "what_they_never_fabricate": ["specific experience timeline", "exact availability", "local address and contact details", "concrete numbers about past experience"]
  },
  
  "style_fingerprints": {
    "sentence_patterns": ["Mix of medium compound sentences with occasional short declarative statements", "Uses em-dashes for emphasis", "Ends paragraphs with strong, memorable phrases"],
    "paragraph_rhythm": "Structured with clear topic headers followed by detailed explanations, building from personal connection to specific qualifications to concrete logistics",
    "tone": "Warm, genuine, and confident without being boastful",
    "technical_depth": "Specific about practical skills and logistics while keeping focus on relationship-building and values alignment"
  },
  
  "signature_elements": {
    "analogies": ["Coffee shop as community space", "Every interaction as opportunity to brighten someone's day"],
    "examples": ["Draws from restaurant service experience", "Uses animal fostering as character reference", "References specific local knowledge"],
    "interaction_style": "Direct address to hiring team with personal connection to company values and mission"
  },
  
  "anti_patterns": {
    "never_uses": ["corporate jargon", "buzzwords like 'synergy' or 'leverage'", "generic phrases like 'hard worker'", "exaggerated claims"],
    "avoids": ["Traditional formal business letter structure", "Overly salesy language", "Generic compliments about the company", "Vague personality descriptions without backing examples"]
  }
}

def get_random_story():
    """Pick a random story from static/stories"""
    story_files = glob.glob(os.path.join('static', 'stories', '*.txt'))
    if not story_files:
        raise FileNotFoundError("No story files found in static/stories/")
    
    selected = random.choice(story_files)
    print(f"📖 Selected story: {os.path.basename(selected)}")
    
    with open(selected, 'r', encoding='utf-8') as f:
        return f.read()

def test_direct_anthropic(style, news):
    """Test direct Anthropic API"""
    print("\n" + "="*70)
    print("🤖 Testing: DIRECT ANTHROPIC API (Claude Sonnet 4)")
    print("="*70)
    
    start = time.time()
    
    try:
        styled_text = restyle_content(style, news)
        duration = time.time() - start
        
        # Rough cost estimate (Claude Sonnet 4 pricing)
        input_tokens = (len(str(style)) + len(news)) / 4
        output_tokens = len(styled_text) / 4
        cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
        
        print(f"✅ SUCCESS")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"📝 Output length: {len(styled_text)} characters")
        print(f"💰 Cost: ${cost:.6f}")
        
        return {
            'success': True,
            'duration': duration,
            'cost': cost,
            'output': styled_text,
            'output_length': len(styled_text)
        }
    
    except Exception as e:
        duration = time.time() - start
        print(f"❌ FAILED after {duration:.2f}s")
        print(f"Error: {e}")
        return {
            'success': False,
            'duration': duration,
            'error': str(e)
        }

def test_replicate_claude(style, news):
    """Test Replicate's Claude"""
    print("\n" + "="*70)
    print("🤖 Testing: REPLICATE CLAUDE 4.5 SONNET")
    print("="*70)
    
    # Build the prompt (same format as your restyle_with_model endpoint)
    prompt = f"""You are a writing style adapter. You have been given:

1. A detailed JSON style profile of a writer
2. An AI news article

Your task: Rewrite the news article to match the writer's style perfectly.

STYLE PROFILE:
{json.dumps(style, indent=2)}

ORIGINAL ARTICLE:
{news}

Instructions:
- Apply ALL patterns from the style profile
- Match their conversational voice markers and recurring phrases
- Use their sentence structures and paragraph rhythm
- Incorporate their authenticity markers
- Follow their opening and closing patterns
- Avoid their anti-patterns
- Keep the same factual content but transform the voice completely

Output ONLY the rewritten article, no explanations."""
    
    start = time.time()
    
    try:
        # Use the SHORT KEY format that generate() expects
        success, text, cost = generate("claude-4.5-sonnet", prompt, 4000)
        duration = time.time() - start
        
        if success:
            print(f"✅ SUCCESS")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"📝 Output length: {len(text)} characters")
            print(f"💰 Cost: ${cost:.6f}")
            
            return {
                'success': True,
                'duration': duration,
                'cost': cost,
                'output': text,
                'output_length': len(text)
            }
        else:
            print(f"❌ FAILED after {duration:.2f}s")
            print(f"Error: {text}")
            return {
                'success': False,
                'duration': duration,
                'error': text
            }
    
    except Exception as e:
        duration = time.time() - start
        print(f"❌ FAILED after {duration:.2f}s")
        print(f"Error: {e}")
        return {
            'success': False,
            'duration': duration,
            'error': str(e)
        }

def main():
    print("🚀 SPEED TEST: Replicate Claude vs Direct Anthropic API")
    print("="*70)
    
    # Get a random story
    try:
        story = get_random_story()
        print(f"📰 Story length: {len(story)} characters\n")
    except Exception as e:
        print(f"❌ Error loading story: {e}")
        return
    
    # Convert style to JSON string
    style_json = json.dumps(STYLE_PROFILE)
    
    # Test both versions
    direct_result = test_direct_anthropic(style_json, story)
    replicate_result = test_replicate_claude(STYLE_PROFILE, story)
    
    # Print comparison
    print("\n" + "="*70)
    print("📊 COMPARISON")
    print("="*70)
    
    if direct_result['success'] and replicate_result['success']:
        print("\n⏱️  SPEED:")
        print(f"   Direct Anthropic:  {direct_result['duration']:.2f}s")
        print(f"   Replicate Claude:  {replicate_result['duration']:.2f}s")
        
        if direct_result['duration'] < replicate_result['duration']:
            diff = replicate_result['duration'] - direct_result['duration']
            pct = (diff / replicate_result['duration']) * 100
            print(f"   🏆 Winner: Direct Anthropic ({diff:.2f}s faster, {pct:.1f}% improvement)")
        else:
            diff = direct_result['duration'] - replicate_result['duration']
            pct = (diff / direct_result['duration']) * 100
            print(f"   🏆 Winner: Replicate ({diff:.2f}s faster, {pct:.1f}% improvement)")
        
        print("\n💰 COST:")
        print(f"   Direct Anthropic:  ${direct_result['cost']:.6f}")
        print(f"   Replicate Claude:  ${replicate_result['cost']:.6f}")
        
        cost_diff = abs(direct_result['cost'] - replicate_result['cost'])
        print(f"   Difference: ${cost_diff:.6f}")
        
        print("\n📝 OUTPUT:")
        print(f"   Direct Anthropic:  {direct_result['output_length']} characters")
        print(f"   Replicate Claude:  {replicate_result['output_length']} characters")
    else:
        print("\n⚠️  Could not compare - one or both tests failed")
        if not direct_result['success']:
            print(f"   Direct Anthropic failed: {direct_result.get('error')}")
        if not replicate_result['success']:
            print(f"   Replicate failed: {replicate_result.get('error')}")
    
    # Show output previews
    if direct_result['success']:
        print("\n" + "="*70)
        print("📄 DIRECT ANTHROPIC OUTPUT (first 300 chars):")
        print("="*70)
        print(direct_result['output'][:300] + "...")
    
    if replicate_result['success']:
        print("\n" + "="*70)
        print("📄 REPLICATE CLAUDE OUTPUT (first 300 chars):")
        print("="*70)
        print(replicate_result['output'][:300] + "...")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    main()