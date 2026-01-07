from flask import Flask, render_template, request, jsonify
from utilities.anthropic_utils import fetch_and_analyze, generate_articles, search_sources

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

@app.route('/')
def home():
    return render_template('index.html', topics=TOPICS)

@app.route('/generate', methods=['POST'])
def generate():
    topic_key = request.form.get('topic')
    custom_topic = request.form.get('custom_topic', '').strip()
    files = request.files.getlist('files')

    if not files:
        return jsonify({"error": "Upload at least one writing sample"}), 400

    topic = custom_topic if custom_topic else TOPICS.get(topic_key, "technology news")

    # Parallel: fetch sources + analyze style
    sources, style = fetch_and_analyze(topic, files)

    if not sources:
        return jsonify({"error": f"No articles found for '{topic}'"}), 404

    # Generate articles
    articles = generate_articles(sources, style)

    return jsonify({"articles": articles, "style": style, "topic": topic})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
