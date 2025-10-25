from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import json
import os
import logging
import random
import glob
from utilities.anthropic_utils import analyze_writing_style, restyle_text_with_claude, chat_with_streaming
from utilities.google_secret_utils import get_secret
from utilities.replicate_utils import generate_with_replicate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(levelname)s-%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_random_story():
    """Pick a random .txt file from static/stories directory"""
    story_dir = os.path.join('static', 'stories')
    story_files = glob.glob(os.path.join(story_dir, '*.txt'))
    
    if not story_files:
        logger.error(f"❌ No story files found in {story_dir}")
        return "No stories available. Please add .txt files to static/stories directory."
    
    selected_story = random.choice(story_files)
    logger.info(f"📖 Selected story: {os.path.basename(selected_story)}")
    
    try:
        with open(selected_story, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"✅ Loaded story: {len(content)} characters")
        return content
    except Exception as e:
        logger.error(f"❌ Error reading story file: {e}")
        return "Error loading story."

@app.route('/')
def home():
    logger.info("🏠 Home page loaded")
    return render_template('style.html')

@app.route('/chat')
def chat_page():
    logger.info("💬 Chat page loaded")
    models = {
        'Claude Sonnet 4': 'claude-sonnet-4-20250514',
        'Claude Sonnet 3.5': 'claude-3-5-sonnet-20241022',
        'Claude Opus 3': 'claude-3-opus-20240229',
        'Claude Haiku 3.5': 'claude-3-5-haiku-20241022'
    }
    return render_template('chat.html', models=models)

@app.route('/analyze', methods=['POST'])
def analyze():
    logger.info("="*80)
    logger.info("📄 /analyze ENDPOINT CALLED")
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    saved_files = []
    file_info = []
    
    logger.info(f"📁 Received {len(files)} files:")
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            saved_files.append(filepath)
            
            size_kb = os.path.getsize(filepath) / 1024
            logger.info(f"   📎 {filename} ({size_kb:.1f} KB)")
            file_info.append({'name': filename, 'size': size_kb})
    
    if not saved_files:
        return jsonify({'error': 'No valid files uploaded'}), 400
    
    try:
        logger.info("🔬 Starting style analysis...")
        style_json = analyze_writing_style(saved_files)
        
        logger.info("✅ ANALYSIS COMPLETE")
        logger.info(f"📊 Style JSON type: {type(style_json)}")
        logger.info("="*80)
        
        return jsonify({
            'style': style_json,
            'files_processed': file_info
        })
    
    except Exception as e:
        logger.error(f"❌ Error in analysis: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/get_news', methods=['GET'])
def get_news():
    """Returns a random story from static/stories/*.txt"""
    logger.info("="*80)
    logger.info("📖 /get_news ENDPOINT CALLED (returning random story)")
    
    try:
        story = get_random_story()
        
        logger.info("✅ STORY RETRIEVAL COMPLETE")
        logger.info(f"📰 Story length: {len(story)} characters")
        logger.info("="*80)
        
        return jsonify({'news': story})
    
    except Exception as e:
        logger.error(f"❌ Error getting story: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/restyle', methods=['POST'])
def restyle():
    logger.info("="*80)
    logger.info("🎨 /restyle ENDPOINT CALLED")
    
    data = request.get_json()
    style = data.get('style')
    news = data.get('news')
    
    if not style or not news:
        return jsonify({'error': 'Missing style or news data'}), 400
    
    claude_version = data.get('claude_version', 'claude-sonnet-4-20250514')
    logger.info(f"🤖 Using {claude_version}")
    
    try:
        import time
        start_time = time.time()
        
        styled_text, cost = restyle_text_with_claude(style, news, claude_version)
        
        duration = time.time() - start_time
        
        logger.info("✅ RESTYLE COMPLETE")
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        logger.info(f"📝 Output length: {len(styled_text)} characters")
        logger.info(f"💰 Cost: ${cost:.6f}")
        logger.info("="*80)
        
        return jsonify({
            'styled': styled_text,
            'cost': cost,
            'duration': duration
        })
    
    except Exception as e:
        logger.error(f"❌ Error in restyle: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/available_models', methods=['GET'])
def available_models():
    logger.info("📋 /available_models called")
    
    models = {
        'gpt-5-nano': {
            'name': 'GPT-5 Nano',
            'type': 'replicate',
            'description': 'Fast and efficient'
        },
        'gpt-5-micro': {
            'name': 'GPT-5 Micro', 
            'type': 'replicate',
            'description': 'Balanced performance'
        },
        'gpt-5-ultra': {
            'name': 'GPT-5 Ultra',
            'type': 'replicate', 
            'description': 'Maximum quality'
        },
        'claude-sonnet-4-20250514': {
            'name': 'Claude Sonnet 4',
            'type': 'anthropic',
            'description': 'Latest and greatest'
        },
        'claude-3-5-sonnet-20241022': {
            'name': 'Claude Sonnet 3.5',
            'type': 'anthropic',
            'description': 'Previous generation'
        },
        'claude-3-5-haiku-20241022': {
            'name': 'Claude Haiku 3.5',
            'type': 'anthropic',
            'description': 'Fast and efficient'
        }
    }
    
    logger.info(f"✅ Returning {len(models)} models")
    return jsonify(models)

@app.route('/restyle_with_model', methods=['POST'])
def restyle_with_model():
    logger.info("="*80)
    logger.info("🎨 /restyle_with_model ENDPOINT CALLED")
    
    data = request.get_json()
    model = data.get('model')
    style = data.get('style')
    news = data.get('news')
    
    logger.info(f"🤖 Model: {model}")
    
    if not all([model, style, news]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        import time
        start_time = time.time()
        
        logger.info("🚀 Generating with model...")
        
        if model.startswith('gpt-'):
            styled_text, cost = generate_with_replicate(model, style, news)
        else:
            styled_text, cost = restyle_text_with_claude(style, news, model)
        
        duration = time.time() - start_time
        
        logger.info("✅ RESTYLE WITH MODEL COMPLETE")
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        logger.info(f"💰 Cost: ${cost:.6f}")
        logger.info(f"📝 Output length: {len(styled_text)} characters")
        logger.info("="*80)
        
        return jsonify({
            'styled': styled_text,
            'cost': cost,
            'duration': duration
        })
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    logger.info("="*80)
    logger.info("💬 /chat ENDPOINT CALLED")
    
    data = request.get_json()
    model = data.get('model', 'claude-sonnet-4-20250514')
    messages = data.get('messages', [])
    temperature = data.get('temperature', 1.0)
    max_tokens = data.get('max_tokens', 1024)
    web_search = data.get('web_search', False)
    thinking = data.get('thinking', False)
    
    logger.info(f"🤖 Model: {model}")
    logger.info(f"💭 Messages: {len(messages)}")
    logger.info(f"🌡️  Temp: {temperature}, 🎯 Max tokens: {max_tokens}")
    logger.info(f"🔍 Web search: {web_search}, 🧠 Thinking: {thinking}")
    
    def generate():
        try:
            for chunk in chat_with_streaming(model, messages, temperature, max_tokens, web_search, thinking):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"❌ Streaming error: {str(e)}", exc_info=True)
            yield f"data: Error: {str(e)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    logger.info("🚀 Starting Flask app...")
    app.run(host='0.0.0.0', port=8081, debug=True)