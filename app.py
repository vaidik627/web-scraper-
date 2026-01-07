from flask import Flask, render_template, request, jsonify
from scraper.scraper import ScraperEngine
from scraper.summarizer import SummarizerEngine
import logging

app = Flask(__name__)
summarizer = SummarizerEngine()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        data = request.get_json()
        
        # Validate Input
        base_url = data.get('url')
        if not base_url:
            return jsonify({"error": "URL is required"}), 400
            
        config = {
            'max_pages': data.get('max_pages', 5),
            'depth': data.get('depth', 2),
            'links_per_page': data.get('links_per_page', 5),
            'sections': {
                'title': data.get('scrape_title', False),
                'meta_description': data.get('scrape_meta', False),
                'headings': data.get('scrape_headings', False),
                'paragraphs': data.get('scrape_paragraphs', False),
                'tables': data.get('scrape_tables', False),
                'links': data.get('scrape_links', False),
                'images': data.get('scrape_images', False),
            }
        }
        
        logger.info(f"Starting scrape for {base_url} with config: {config}")
        
        engine = ScraperEngine(base_url, config)
        results = engine.run()
        
        if isinstance(results, dict) and "error" in results:
             return jsonify(results), 400
             
        return jsonify({
            "message": "Scraping completed successfully",
            "count": len(results),
            "data": results
        })
        
    except Exception as e:
        logger.error(f"Error in /scrape: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/summarizer')
def summarizer_page():
    return render_template('summarizer.html')

@app.route('/api/summarize', methods=['POST'])
def summarize():
    try:
        data = request.get_json()
        url = data.get('url')
        length = data.get('length', 'medium')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
            
        result = summarizer.generate_summary(url, length)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in /summarize: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
