import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from utilities.anthropic_utils import search_sources, analyze_style, generate_single_article
from utilities.content_filter import check_content_filter

app = Flask(__name__)

# Rate limiter - prevents abuse and controls costs
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"],  # General site limit
    storage_uri="memory://"
)

TOPICS = {
    "tech": "AI and technology news",
    "politics": "US political news",
    "sports": "sports news",
    "medicine": "medical and healthcare news",
    "finance": "financial markets and business news",
    "climate": "climate and environment news",
    "entertainment": "entertainment and media news"
}

SAMPLE_STYLE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'files', 'sample.txt')

@app.route('/')
def home():
    return render_template('index.html', topics=TOPICS)

@app.route('/generate', methods=['POST'])
@limiter.limit("10 per hour")  # Strict limit on expensive AI endpoint
def generate():
    """Stream articles as they're generated using SSE

    Rate limited to 10 requests per hour per IP to prevent abuse
    and control API costs (~$0.12 per request)
    """
    custom_topic = request.form.get('custom_topic', '').strip()
    files = request.files.getlist('files')
    use_sample_style = request.form.get('use_sample_style') == 'on'

    files = [f for f in files if f.filename]

    if not files and not use_sample_style:
        return jsonify({"error": "Upload writing samples or use the sample style"}), 400

    if not custom_topic:
        return jsonify({"error": "Enter a topic to write about"}), 400

    # Content filter check
    is_allowed, filter_error = check_content_filter(custom_topic)
    if not is_allowed:
        return jsonify({"error": filter_error}), 400

    sample_content = None
    if use_sample_style and not files:
        try:
            with open(SAMPLE_STYLE_PATH, 'r') as f:
                sample_content = f.read()
        except FileNotFoundError:
            return jsonify({"error": "Sample style file not found"}), 500

    # Read file contents before entering generator (can't read in generator)
    file_contents = []
    for f in files:
        file_contents.append({
            'filename': f.filename,
            'data': f.read()
        })

    def generate_stream():
        # Send initial event
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching for articles...'})}\n\n"

        # Search for sources
        sources = search_sources(custom_topic)
        if not sources:
            yield f"data: {json.dumps({'type': 'error', 'message': f'No articles found for {custom_topic}'})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'sources', 'count': len(sources)})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(sources)} sources. Analyzing your writing style...'})}\n\n"

        # Analyze style
        style = analyze_style(file_contents if file_contents else None, sample_content)

        yield f"data: {json.dumps({'type': 'status', 'message': 'Style analyzed. Generating articles...'})}\n\n"

        # Generate and stream each article one by one
        for i, src in enumerate(sources):
            yield f"data: {json.dumps({'type': 'status', 'message': f'Writing article {i+1} of {len(sources)}...'})}\n\n"

            article = generate_single_article(src, style, i)
            yield f"data: {json.dumps({'type': 'article', 'index': i, 'article': article})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    response = Response(
        stream_with_context(generate_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
