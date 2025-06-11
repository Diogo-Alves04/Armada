from flask import Flask, jsonify, request, render_template, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
import json
import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI
import base64
from expiration_estimates import EXPIRATION_ESTIMATES

# --- Configuration Classes ---
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

# --- Flask App Setup ---
app = Flask(__name__, template_folder='.', static_folder='static')
CORS(app)

# --- MongoDB Connection ---
uri = os.environ.get("MONGODB_URI", "mongodb+srv://rafaelponzetto:gqfsBrwXCjkocXce@cluster0.i7cmk4l.mongodb.net/foodDB?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(uri)
db = client["foodDB"]
collection = db["items"]

# --- Photo Handler Configuration ---
UPLOAD_FOLDER = 'Uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
"""
# --- Expiration Estimates (in days) ---
EXPIRATION_ESTIMATES = {
    "milk": 7, "yogurt": 14, "cheese": 30, "butter": 30, "cream": 10,
    "eggs": 28, "bread": 7, "muffin": 7, "cake": 7, "pasta": 365,
    "rice": 365, "cereal": 180, "oats": 365, "flour": 180, "sugar": 90,
    "apple": 30, "banana": 7, "orange": 21, "grapes": 14, "strawberry": 5,
    "carrot": 30, "lettuce": 7, "tomato": 14, "potato": 30, "onion": 60,
    "chicken": 2, "beef": 3, "pork": 3, "fish": 2, "shrimp": 2,
    "water": 365, "juice": 90, "soda": 180, "beer": 180, "wine": 365,
    "canned soup": 365, "canned beans": 365, "canned vegetables": 365,
    "jam": 365, "peanut butter": 180, "honey": 730, "olive oil": 365,
    "ketchup": 365, "mustard": 365, "mayonnaise": 90
}
"""
# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def serialize_item(item):
    item['_id'] = str(item['_id'])
    if 'expiration_date' in item and isinstance(item['expiration_date'], datetime):
        item['expiryDate'] = item['expiration_date'].strftime('%Y-%m-%d')
    item['category'] = str(item.get('category', 'other'))
    return item

def save_analysis_result(filename, analysis_data):
    """Save analysis results to JSON file"""
    result_filename = f"analysis_{os.path.splitext(filename)[0]}.json"
    result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
    
    with open(result_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "items": analysis_data
        }, f, indent=2)
    
    logger.info(f"Analysis results saved to {result_path}")
    return result_path

def estimate_expiration(product_name: str) -> int:
    """Estimate expiration in days based on product name"""
    product_name = product_name.lower().strip()
    for key in EXPIRATION_ESTIMATES:
        if key in product_name:
            return EXPIRATION_ESTIMATES[key]
    logger.warning(f"No expiration estimate for {product_name}, defaulting to 14 days")
    return 14

def analyze_image_with_AI(image_path: str) -> dict:
    """Send image to AI for analysis"""
    try:
        client = OpenAI(
            base_url=settings.ai.base_url,
            api_key=settings.ai.api_key
        )
        
        prompt = """
        Analyze the provided image, which shows various packaged products.
        Identify each distinct product and count how many units of each are visible.
        Respond ONLY with a JSON array of objects in the following format:
        [{"product": <product_name>, "quantity": <integer count>}]
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
        
        try:
            parsed = json.loads(response.choices[0].message.content)
            for item in parsed:
                item['expiration'] = estimate_expiration(item['product'])
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

# --- Photo Handler Routes ---
@app.route('/photo_handler', methods=['POST'])
def handle_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo uploaded'}), 400
    
    photo = request.files['photo']
    if photo.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not allowed_file(photo.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{secure_filename(photo.filename)}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        photo.save(save_path)
        logger.info(f"Photo saved: {save_path}")
        
        ai_result = analyze_image_with_AI(save_path)
        
        if ai_result['status'] == 'error':
            return jsonify({
                'status': 'partial_success',
                'message': 'Photo saved but AI analysis failed',
                'error': ai_result['message'],
                'photo_path': f"/Uploads/{filename}"
            }), 207
        
        save_analysis_result(filename, ai_result['analysis'])
        
        added_items = []
        for item in ai_result['analysis']:
            product_name = item.get('product', '').strip()
            quantity = item.get('quantity', 0)
            expiration_days = item.get('expiration', 14)
            
            if not product_name or not isinstance(quantity, int) or not isinstance(expiration_days, int):
                logger.warning(f"Skipping invalid item: {item}")
                continue
            
            expiration_date = datetime.now() + timedelta(days=expiration_days)
            
            existing_item = collection.find_one({
                "name": product_name,
                "expiration_date": {"$gte": expiration_date - timedelta(days=1), "$lte": expiration_date + timedelta(days=1)}
            })
            
            if existing_item:
                updated_quantity = existing_item['quantity'] + quantity
                collection.update_one(
                    {"_id": existing_item['_id']},
                    {"$set": {"quantity": updated_quantity, "added_on": datetime.now()}}
                )
                added_items.append(serialize_item(collection.find_one({"_id": existing_item['_id']})))
                logger.info(f"Updated existing item: {product_name}, new quantity: {updated_quantity}")
            else:
                new_item = {
                    "name": product_name,
                    "category": "ai_detected",
                    "expiration_date": expiration_date,
                    "quantity": quantity,
                    "unit": "units",
                    "added_on": datetime.now(),
                    "source": "photo_analysis",
                    "image_file": filename
                }
                result = collection.insert_one(new_item)
                added_item = collection.find_one({"_id": result.inserted_id})
                added_items.append(serialize_item(added_item))
                logger.info(f"Added new item: {product_name} to MongoDB")
        
        return jsonify({
            'status': 'success',
            'message': 'Photo analyzed, results saved, and items directly added to database',
            'photo_path': f"/Uploads/{filename}",
            'analysis': ai_result['analysis'],
            'added_items': added_items
        })
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Processing failed: {str(e)}'
        }), 500

# --- API Routes ---
@app.route('/api/items', methods=['GET'])
def get_items():
    try:
        query = {}
        search_term = request.args.get('search', '')
        if search_term:
            query['name'] = {'$regex': search_term, '$options': 'i'}

        sort_by_expiry = request.args.get('sorted', 'false').lower() == 'true'
        
        if sort_by_expiry:
            food_items_cursor = collection.find(query).sort("expiration_date", 1)
        else:
            food_items_cursor = collection.find(query)

        food_items = [serialize_item(item) for item in list(food_items_cursor)]
        return jsonify(food_items)
    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/items', methods=['POST'])
def add_item():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['name', 'category', 'expiryDate', 'quantity', 'unit']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        try:
            expiration_date_obj = datetime.strptime(data['expiryDate'], '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid expiryDate format. Please use YYYY-MM-DD."}), 400

        new_item = {
            "name": data['name'],
            "category": str(data['category']).lower(),
            "expiration_date": expiration_date_obj,
            "quantity": int(data['quantity']),
            "unit": data['unit'],
            "added_on": datetime.now()
        }

        result = collection.insert_one(new_item)
        if result.inserted_id:
            added_item = collection.find_one({"_id": result.inserted_id})
            return jsonify(serialize_item(added_item)), 201
        else:
            return jsonify({"error": "Failed to add item to database."}), 500
    except Exception as e:
        logger.error(f"Error adding item: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/items/<id>', methods=['DELETE'])
def delete_item(id):
    try:
        if not ObjectId.is_valid(id):
            return jsonify({"error": "Invalid item ID format."}), 400

        item = collection.find_one({"_id": ObjectId(id)})
        if not item:
            return jsonify({"error": "Item not found."}), 404

        if item['quantity'] > 1:
            collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": {"quantity": item['quantity'] - 1, "added_on": datetime.now()}}
            )
            updated_item = collection.find_one({"_id": ObjectId(id)})
            return jsonify({
                "message": f"Quantity of {item['name']} reduced by 1",
                "item": serialize_item(updated_item)
            }), 200
        else:
            result = collection.delete_one({"_id": ObjectId(id)})
            if result.deleted_count == 1:
                return jsonify({"message": f"Item {item['name']} deleted successfully."}), 200
            else:
                return jsonify({"error": "Item not found or already deleted."}), 404
    except Exception as e:
        logger.error(f"Error processing item {id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/items/<id>/increment', methods=['POST'])
def increment_item(id):
    try:
        if not ObjectId.is_valid(id):
            return jsonify({"error": "Invalid item ID format."}), 400

        item = collection.find_one({"_id": ObjectId(id)})
        if not item:
            return jsonify({"error": "Item not found."}), 404

        updated_quantity = item['quantity'] + 1
        collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"quantity": updated_quantity, "added_on": datetime.now()}}
        )
        updated_item = collection.find_one({"_id": ObjectId(id)})
        return jsonify({
            "message": f"Quantity of {item['name']} increased by 1",
            "item": serialize_item(updated_item)
        }), 200
    except Exception as e:
        logger.error(f"Error incrementing item {id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/items/<id>/update_expiry', methods=['PATCH'])
def update_expiry(id):
    try:
        if not ObjectId.is_valid(id):
            return jsonify({"error": "Invalid item ID format."}), 400

        item = collection.find_one({"_id": ObjectId(id)})
        if not item:
            return jsonify({"error": "Item not found."}), 404

        data = request.get_json()
        if not data or 'expiryDate' not in data:
            return jsonify({"error": "Missing expiryDate field."}), 400

        try:
            expiration_date_obj = datetime.strptime(data['expiryDate'], '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid expiryDate format. Please use YYYY-MM-DD."}), 400

        collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"expiration_date": expiration_date_obj, "added_on": datetime.now()}}
        )
        updated_item = collection.find_one({"_id": ObjectId(id)})
        return jsonify({
            "message": f"Expiry date updated for {item['name']}",
            "item": serialize_item(updated_item)
        }), 200
    except Exception as e:
        logger.error(f"Error updating expiry for item {id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/analysis_results', methods=['GET'])
def get_analysis_results():
    try:
        results_folder = app.config['RESULTS_FOLDER']
        analysis_files = [f for f in os.listdir(results_folder) if f.endswith('.json')]
        
        results = []
        for filename in analysis_files:
            with open(os.path.join(results_folder, filename), 'r') as f:
                data = json.load(f)
                data['filename'] = filename
                results.append(data)
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching analysis results: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analysis_results/<filename>', methods=['GET'])
def get_single_analysis(filename):
    try:
        if not filename.endswith('.json'):
            filename += '.json'
            
        filepath = os.path.join(app.config['RESULTS_FOLDER'], filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Analysis not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/legacy')
def home():
    return """
    <h1>AI Photo Analysis System</h1>
    <p>Send photos via POST to /photo_handler</p>
    <p>Photos will be automatically analyzed by AI</p>
    """

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)