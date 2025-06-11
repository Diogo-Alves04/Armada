from flask import Flask, request, jsonify, send_from_directory
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from openai import OpenAI
import base64
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import json

# Configuration classes
class AISetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='ai_', env_file='.env', extra='ignore')
    base_url: str = Field(default="https://api.studio.nebius.ai/v1/")
    model: str = Field(default="Qwen/Qwen2-VL-72B-Instruct")
    api_key: str

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    project_name: str = Field(default="computer_vision")
    ai: AISetting = AISetting()

settings = Settings()

# Flask App Setup
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_analysis_result(filename, analysis_data):
    """Save analysis results to JSON file"""
    result_filename = f"analysis_{os.path.splitext(filename)[0]}.json"
    result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
    
    with open(result_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "image_file": filename,
            "analysis": analysis_data
        }, f, indent=2)
    
    logger.info(f"Analysis results saved to {result_path}")
    return result_path

def analyze_image_with_ai(image_path: str) -> dict:
    """Send image to AI for analysis"""
    try:
        client = OpenAI(
            base_url=settings.ai.base_url,
            api_key=settings.ai.api_key
        )
        
        prompt = """
        Analyze the provided image, which shows various packaged products.
        Identify each distinct product, count how many units of each are visible and their expiration dates in days.
        Respond ONLY with a JSON array of objects in the following format:
        [{"product": <product_name>, "quantity": <integer count>,"expiration": <integer expiration date in days> }]
        Strictly follow the format.
        Do not include any extra text, comments, or formatting—only output valid JSON.
        """

        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        response = client.chat.completions.create(
            model=settings.ai.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.6
        )
        
        # Validate JSON response
        try:
            parsed = json.loads(response.choices[0].message.content)
            return {
                "status": "success",
                "analysis": parsed
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from AI: {str(e)}")
            return {
                "status": "error",
                "message": "AI returned invalid JSON format"
            }
            
    except Exception as e:
        logger.error(f"AI analysis failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.route('/')
def home():
    return """
    <h1>AI Photo Analysis System</h1>
    <p>Send photos via POST to /photo_handler</p>
    <p>Photos will be automatically analyzed by AI</p>
    """

@app.route('/photo_handler', methods=['POST'])
def handle_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo uploaded'}), 400
    
    photo = request.files['photo']
    if photo.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not allowed_file(photo.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Save the photo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{secure_filename(photo.filename)}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        photo.save(save_path)
        logger.info(f"Photo saved: {save_path}")
        
        # Send to AI for analysis
        ai_result = analyze_image_with_ai(save_path)
        
        if ai_result['status'] == 'error':
            return jsonify({
                'status': 'partial_success',
                'message': 'Photo saved but AI analysis failed',
                'error': ai_result['message'],
                'photo_path': f"/uploads/{filename}"
            }), 207
        
        # Save analysis results to JSON file
        save_analysis_result(filename, ai_result['analysis'])
        
        return jsonify({
            'status': 'success',
            'message': 'Photo analyzed and results saved',
            'photo_path': f"/uploads/{filename}"
        })
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Processing failed: {str(e)}'
        }), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/results')
def list_results():
    """Endpoint to list all analysis results (for debugging)"""
    results = []
    for filename in os.listdir(app.config['RESULTS_FOLDER']):
        if filename.endswith('.json'):
            results.append(filename)
    return jsonify(results)

@app.route('/results/<filename>')
def get_result(filename):
    """Endpoint to view a specific result (for debugging)"""
    if not filename.endswith('.json'):
        filename += '.json'
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)