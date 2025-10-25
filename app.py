import os,sys,subprocess,webbrowser,threading,time,logging,concurrent.futures,random,glob
from flask import Flask,render_template,request,jsonify,Response
from utilities.anthropic_utils import analyze_style_and_fetch_news,restyle_content,stream_chat,fetch_news_only
from utilities.replicate_utils import generate,get_models

logging.basicConfig(level=logging.INFO,format='%(asctime)s-%(levelname)s-%(message)s')
logger=logging.getLogger(__name__)

app=Flask(__name__)
MODELS={"Sonnet 3.5 (Fast)":"claude-3-5-sonnet-latest","Sonnet 4 (Balanced)":"claude-sonnet-4-20250514","Opus 4.1 (Smartest)":"claude-opus-4-1-20250805","Haiku 3.5 (Fastest)":"claude-3-5-haiku-latest"}

# News cache - 5min TTL
NEWS_CACHE={"news":None,"ts":0}

def kill_port_5000():
    try:
        result=subprocess.run(['lsof','-ti:5000'],capture_output=True,text=True,timeout=5)
        if result.returncode==0 and result.stdout.strip():
            for pid in result.stdout.strip().split('\n'):
                try:logger.info(f"🔥 Kill {pid}");subprocess.run(['kill','-9',pid],timeout=5)
                except Exception as e:logger.warning(f"Could not kill {pid}: {e}")
        else:logger.info("✅ Port free")
    except:subprocess.run(['pkill','-f','flask.*5000'],timeout=5)

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
    return render_template('chat.html',models=MODELS)

@app.route('/prefetch_news')
def prefetch_news():
    """Pre-fetch news on file button click - now returns random static story"""
    logger.info("="*80)
    logger.info("📡 /prefetch_news ENDPOINT CALLED")
    logger.info("⏱️  Request received at: %s", time.strftime('%H:%M:%S'))
    
    now=time.time()
    
    # Check cache
    if NEWS_CACHE["news"] and (now-NEWS_CACHE["ts"])<300:
        cache_age = int(now - NEWS_CACHE["ts"])
        logger.info("💾 RETURNING CACHED NEWS")
        logger.info(f"📊 Cache age: {cache_age} seconds (TTL: 300s)")
        logger.info(f"📰 News length: {len(NEWS_CACHE['news'])} characters")
        logger.info("="*80)
        return jsonify({"news":NEWS_CACHE["news"],"cached":True})
    
    # Get random story instead of fetching news
    logger.info("🔄 Cache expired or empty - getting random story")
    fetch_start = time.time()
    
    try:
        logger.info("🚀 Calling get_random_story()...")
        news=get_random_story()
        
        fetch_duration = time.time() - fetch_start
        NEWS_CACHE["news"]=news
        NEWS_CACHE["ts"]=now
        
        logger.info("✅ STORY RETRIEVAL COMPLETE")
        logger.info(f"⏱️  Fetch duration: {fetch_duration:.2f}s")
        logger.info(f"📰 Story length: {len(news)} characters")
        logger.info(f"💾 Cached for 300 seconds")
        logger.info("="*80)
        
        return jsonify({"news":news,"cached":False})
    except Exception as e:
        fetch_duration = time.time() - fetch_start
        logger.error("="*80)
        logger.error("❌ STORY RETRIEVAL ERROR")
        logger.error(f"⏱️  Failed after: {fetch_duration:.2f}s")
        logger.error(f"📛 Error: {e}")
        logger.error("="*80)
        return jsonify({"error":str(e)}),500

@app.route('/analyze',methods=['POST'])
def analyze():
    """Analyze writing style from uploaded files"""
    logger.info("="*80)
    logger.info("📄 /analyze ENDPOINT CALLED")
    
    files=request.files.getlist('files')
    if not files:
        logger.warning("⚠️  No files provided")
        return jsonify({'error':'No files'}),400
    if len(files)>5:
        logger.warning("⚠️  Too many files: %d", len(files))
        return jsonify({'error':'Max 5 files'}),400
    
    logger.info(f"📁 Received {len(files)} files:")
    for f in files:
        logger.info(f"   📎 {f.filename} ({len(f.read())/1024:.1f} KB)")
        f.seek(0)  # Reset file pointer after reading size
    
    analyze_start = time.time()
    logger.info("🔬 Starting style analysis...")
    
    try:
        style_json,news = analyze_style_and_fetch_news(files)
        
        analyze_duration = time.time() - analyze_start
        logger.info("✅ ANALYSIS COMPLETE")
        logger.info(f"⏱️  Total duration: {analyze_duration:.2f}s")
        logger.info(f"📊 Style JSON type: {type(style_json).__name__}")
        logger.info("="*80)
        
        return jsonify({'style_json':style_json,'news':news})
    except Exception as e:
        analyze_duration = time.time() - analyze_start
        logger.error("❌ ANALYSIS ERROR")
        logger.error(f"⏱️  Failed after: {analyze_duration:.2f}s")
        logger.error(f"📛 Error: {e}",exc_info=True)
        logger.error("="*80)
        return jsonify({'error':str(e)}),500

@app.route('/analyze_style',methods=['POST'])
def analyze_style():
    """Legacy endpoint - redirects to /analyze"""
    logger.info("⚠️  Legacy /analyze_style called, processing...")
    return analyze()

@app.route('/restyle',methods=['POST'])
def restyle():
    logger.info("="*80)
    logger.info("🎨 /restyle ENDPOINT CALLED")
    
    data=request.json
    if not data.get('style')or not data.get('news'):
        logger.warning("⚠️  Missing style or news data")
        return jsonify({'error':'Missing data'}),400
    
    logger.info("🤖 Using Claude Sonnet 4")
    restyle_start = time.time()
    
    try:
        styled=restyle_content(data['style'],data['news'])
        
        # Calculate cost (Claude Sonnet 4 pricing)
        # Input: $3/MTok, Output: $15/MTok (approximate)
        input_tokens = (len(str(data['style'])) + len(data['news'])) / 4  # rough estimate
        output_tokens = len(styled) / 4  # rough estimate
        cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
        
        restyle_duration = time.time() - restyle_start
        logger.info("✅ RESTYLE COMPLETE")
        logger.info(f"⏱️  Duration: {restyle_duration:.2f}s")
        logger.info(f"📝 Output length: {len(styled)} characters")
        logger.info(f"💰 Cost: ${cost:.6f}")
        logger.info("="*80)
        
        return jsonify({'styled':styled,'cost':cost})
    except Exception as e:
        restyle_duration = time.time() - restyle_start
        logger.error("❌ RESTYLE ERROR")
        logger.error(f"⏱️  Failed after: {restyle_duration:.2f}s")
        logger.error(f"📛 Error: {e}",exc_info=True)
        logger.error("="*80)
        return jsonify({'error':str(e)}),500

@app.route('/restyle_with_model',methods=['POST'])
def restyle_with_model():
    logger.info("="*80)
    logger.info("🎨 /restyle_with_model ENDPOINT CALLED")
    
    data=request.json
    if not data.get('style')or not data.get('news')or not data.get('model'):
        logger.warning("⚠️  Missing required data")
        return jsonify({'error':'Missing data'}),400
    
    model = data['model']
    logger.info(f"🤖 Model: {model}")
    
    prompt=f"""You are a writing style adapter. You have been given:

1. A detailed JSON style profile of a writer
2. An AI news article (originally written by {data.get('claude_version','Claude Sonnet 4')})

Your task: Rewrite the news article to match the writer's style perfectly.

STYLE PROFILE:
{data['style']}

ORIGINAL NEWS ARTICLE:
{data['news']}

Instructions:
- Apply ALL patterns from the style profile
- Match their conversational voice markers and recurring phrases
- Use their sentence structures and paragraph rhythm
- Incorporate their authenticity markers (how they use specifics, admit uncertainty, etc)
- Follow their opening and closing patterns
- Avoid their anti-patterns
- Keep the same factual content but transform the voice completely

Output ONLY the rewritten article, no explanations."""
    
    restyle_start = time.time()
    logger.info("🚀 Generating with model...")
    
    try:
        success,text,cost=generate(model,prompt,4000)
        
        restyle_duration = time.time() - restyle_start
        
        if not success:
            logger.error("❌ GENERATION FAILED")
            logger.error(f"⏱️  Failed after: {restyle_duration:.2f}s")
            logger.error(f"📛 Error: {text}")
            logger.error("="*80)
            return jsonify({'error':text}),500
        
        logger.info("✅ RESTYLE WITH MODEL COMPLETE")
        logger.info(f"⏱️  Duration: {restyle_duration:.2f}s")
        logger.info(f"💰 Cost: ${cost:.6f}")
        logger.info(f"📝 Output length: {len(text)} characters")
        logger.info("="*80)
        
        return jsonify({'styled':text,'cost':cost,'model':model})
    except Exception as e:
        restyle_duration = time.time() - restyle_start
        logger.error("❌ RESTYLE ERROR")
        logger.error(f"⏱️  Failed after: {restyle_duration:.2f}s")
        logger.error(f"📛 Error: {e}",exc_info=True)
        logger.error("="*80)
        return jsonify({'error':str(e)}),500

@app.route('/available_models',methods=['GET'])
def available_models():
    logger.info("📋 /available_models called")
    models = get_models()
    logger.info(f"✅ Returning {len(models)} models")
    return jsonify({'models':models})

@app.route('/chat',methods=['POST'])
def chat():
    data=request.json
    message=data.get('message','')
    model=data.get('model','claude-3-5-sonnet-latest')
    messages=data.get('messages',[{"role":"user","content":message}])
    temperature=float(data.get('temperature',1.0))
    max_tokens=int(data.get('max_tokens',1024))
    web_search=data.get('web_search',False)
    thinking=data.get('thinking',False)
    
    logger.info("="*80)
    logger.info("💬 CHAT REQUEST")
    logger.info(f"📝 Message: {message[:100]}{'...'if len(message)>100 else''}")
    logger.info(f"🤖 Model: {model}")
    logger.info(f"🔍 Web Search: {web_search}")
    logger.info(f"🧠 Thinking: {thinking}")
    logger.info(f"🌡️  Temperature: {temperature}")
    logger.info(f"📊 Max Tokens: {max_tokens}")
    
    def generate():
        try:
            logger.info("🚀 Initializing client...")
            start=time.time()
            tokens=0
            
            for text in stream_chat(model,messages,temperature,max_tokens,web_search,thinking):
                tokens+=1
                if tokens==1:
                    ttft = time.time()-start
                    logger.info(f"⚡ First token in {ttft:.2f}s")
                yield f"data: {text}\n\n"
            
            elapsed=time.time()-start
            logger.info("✅ CHAT COMPLETE")
            logger.info(f"📊 Tokens: {tokens}")
            logger.info(f"⏱️  Duration: {elapsed:.2f}s")
            logger.info(f"⚡ Speed: {tokens/elapsed:.1f} tok/s")
            yield"data: [DONE]\n\n"
            logger.info("="*80)
            
        except Exception as e:
            logger.error("❌ CHAT ERROR")
            logger.error(f"📛 Error: {e}",exc_info=True)
            logger.error("="*80)
            yield f"data: Error: {str(e)}\n\n"
    
    return Response(generate(),mimetype='text/event-stream')

if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port,debug=True)