from flask import Flask, request, jsonify, send_from_directory
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return """
    <h1>Photo Handler API</h1>
    <p>Send photos via POST to /photo_handler</p>
    <p>Access photos at /uploads/filename.jpg</p>
    <p>List all available photos at /photos</p>
    """

@app.route('/photo_handler', methods=['GET', 'POST'])
def handle_photo():
    if request.method == 'GET':
        return jsonify({
            'instruction': 'Send a photo via POST to this endpoint',
            'parameters': {
                'photo': 'Image file',
                'description': '(optional) Photo description'
            }
        })
    
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo uploaded'}), 400
    
    photo = request.files['photo']
    description = request.form.get('description', '')
    
    if photo.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not allowed_file(photo.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Save the photo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_filename = secure_filename(photo.filename)
    filename = f"{timestamp}_{original_filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        photo.save(save_path)
        file_size = os.path.getsize(save_path)
        
        # Create response
        response = {
            'status': 'success',
            'message': 'Photo uploaded successfully',
            'data': {
                'filename': filename,
                'original_filename': original_filename,
                'description': description,
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'timestamp': timestamp,
                'download_url': f"/uploads/{filename}",
                'view_url': f"/view/{filename}"
            }
        }
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': f'Error saving file: {str(e)}'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/view/<filename>')
def view_photo(filename):
    return f"""
    <h1>View Photo</h1>
    <img src="/uploads/{filename}" style="max-width: 100%;">
    <p><a href="/">Back to home</a></p>
    """

@app.route('/photos')
def list_photos():
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        photo_list = []
        
        for file in files:
            if allowed_file(file):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
                stats = os.stat(file_path)
                photo_list.append({
                    'filename': file,
                    'url': f"/uploads/{file}",
                    'view_url': f"/view/{file}",
                    'size_bytes': stats.st_size,
                    'upload_time': datetime.fromtimestamp(stats.st_ctime).isoformat()
                })
        
        return jsonify({'photos': photo_list, 'count': len(photo_list)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)