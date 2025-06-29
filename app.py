from flask import Flask, jsonify, render_template, send_from_directory
import json
import os
from whiff_watcher import WhiffWatcher
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    """Main dashboard showing whiff watch data"""
    return render_template('index.html')

@app.route('/api/whiff-watch-data')
def get_whiff_watch_data():
    """API endpoint to get current whiff watch data"""
    try:
        watcher = WhiffWatcher()
        data = watcher.generate_whiff_watch_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch whiff watch data",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/generate-json')
def generate_json_file():
    """Generate and save JSON file for Bubble integration"""
    try:
        watcher = WhiffWatcher()
        data = watcher.generate_whiff_watch_data()
        
        # Ensure static directory exists
        os.makedirs('static', exist_ok=True)
        
        # Save to static file for Bubble integration
        with open('static/whiff_watch_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({
            "success": True,
            "message": "JSON file generated successfully",
            "file_path": "/static/whiff_watch_data.json",
            "total_ratings": len(data.get('whiff_watch_ratings', [])),
            "timestamp": data.get('generated_at')
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to generate JSON file",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/static/<path:filename>')
def download_file(filename):
    """Serve static files including the generated JSON"""
    return send_from_directory('static', filename)

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested resource was not found on this server.",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred while processing your request.",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    # Generate initial JSON file on startup
    try:
        watcher = WhiffWatcher()
        data = watcher.generate_whiff_watch_data()
        os.makedirs('static', exist_ok=True)
        with open('static/whiff_watch_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("Initial whiff watch data generated successfully")
    except Exception as e:
        print(f"Warning: Could not generate initial data: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
