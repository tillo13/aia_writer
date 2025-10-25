import os,sys,logging,time
from flask import Flask,render_template,request,jsonify,Response
from utilities.anthropic_utils import analyze_style_and_fetch_news,restyle_content,stream_chat,fetch_news_only
from utilities.replicate_utils import generate,get_models

logging.basicConfig(level=logging.INFO,format='%(asctime)s-%(levelname)s-%(message)s')
logger=logging.getLogger(__name__)

app=Flask(__name__)
MODELS={"Sonnet 3.5 (Fast)":"claude-3-5-sonnet-latest","Sonnet 4 (Balanced)":"claude-sonnet-4-20250514","Opus 4.1 (Smartest)":"claude-opus-4-1-20250805","Haiku 3.5 (Fastest)":"claude-3-5-haiku-latest"}

NEWS_CACHE={"news":None,"ts":0}

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
    logger.info("📡 /prefetch_news ENDPOINT CALLED")
    now=time.time()
    
    if NEWS_CACHE["news"] and (now-NEWS_CACHE["ts"])<300:
        logger.info("💾 RETURNING CACHED NEWS")
        return jsonify({"news":NEWS_CACHE["news"],"cached":True})
    
    logger.info("🔄 Fetching fresh news")
    try:
        news=fetch_news_only()
        NEWS_CACHE["news"]=news
        NEWS_CACHE["ts"]=now
        logger.info("✅ NEWS FETCH COMPLETE")
        return jsonify({"news":news,"cached":False})
    except Exception as e:
        logger.error(f"❌ News fetch error: {e}")
        return jsonify({"error":str(e)}),500

@app.route('/analyze_style',methods=['POST'])
def analyze_style():
    logger.info("📊 /analyze_style called")
    try:
        files=request.files.getlist('files')
        docs=[]
        for f in files:
            content=f.read().decode('utf-8',errors='ignore')
            docs.append(content)
        
        logger.info(f"📄 Processing {len(docs)} documents")
        style,news=analyze_style_and_fetch_news(docs)
        logger.info("✅ Style analysis complete")
        return jsonify({'style':style,'news':news})
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error':str(e)}),500

@app.route('/restyle',methods=['POST'])
def restyle():
    logger.info("✍️ /restyle called")
    try:
        data=request.json
        style=data.get('style')
        news=data.get('news')
        
        text,cost=restyle_content(style,news)
        logger.info(f"✅ Restyle complete - Cost: ${cost:.6f}")
        return jsonify({'styled':text,'cost':cost})
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error':str(e)}),500

@app.route('/restyle_with_model',methods=['POST'])
def restyle_with_model():
    logger.info("🎨 /restyle_with_model called")
    try:
        data=request.json
        style=data.get('style')
        news=data.get('news')
        model=data.get('model','claude-sonnet-4-20250514')
        
        text,cost=restyle_content(style,news,model=model)
        logger.info(f"✅ Restyle complete - Model: {model} - Cost: ${cost:.6f}")
        return jsonify({'styled':text,'cost':cost,'model':model})
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return jsonify({'error':str(e)}),500

@app.route('/available_models',methods=['GET'])
def available_models():
    logger.info("📋 /available_models called")
    models=get_models()
    return jsonify({'models':models})

@app.route('/chat',methods=['POST'])
def chat():
    data=request.json
    messages=data.get('messages',[])
    model=data.get('model','claude-3-5-sonnet-latest')
    temperature=data.get('temperature',1.0)
    max_tokens=data.get('max_tokens',1024)
    web_search=data.get('web_search',False)
    thinking=data.get('thinking',False)
    
    def generate():
        try:
            for chunk in stream_chat(messages,model,temperature,max_tokens,web_search,thinking):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return Response(generate(),mimetype='text/event-stream')

@app.route('/health')
def health():
    return jsonify({'status':'healthy'}),200

if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port,debug=True)