import os
from flask import Flask, render_template, request, jsonify
from utilities.anthropic_utils import fetch_and_analyze, generate_articles

app = Flask(__name__)

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
def generate():
    custom_topic = request.form.get('custom_topic', '').strip()
    files = request.files.getlist('files')
    use_sample_style = request.form.get('use_sample_style') == 'on'

    # Filter out empty file uploads
    files = [f for f in files if f.filename]

    if not files and not use_sample_style:
        return jsonify({"error": "Upload writing samples or use the sample style"}), 400

    if not custom_topic:
        return jsonify({"error": "Enter a topic to write about"}), 400

    # Use sample style file if checkbox is checked and no files uploaded
    sample_content = None
    if use_sample_style and not files:
        try:
            with open(SAMPLE_STYLE_PATH, 'r') as f:
                sample_content = f.read()
        except FileNotFoundError:
            return jsonify({"error": "Sample style file not found"}), 500

    # Parallel: fetch sources + analyze style
    sources, style = fetch_and_analyze(custom_topic, files, sample_content)

    if not sources:
        return jsonify({"error": f"No articles found for '{custom_topic}'"}), 404

    # Generate articles
    articles = generate_articles(sources, style)

    return jsonify({"articles": articles, "style": style, "topic": custom_topic})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
