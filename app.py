# app.py
"""
Enhanced Flask backend for ANPR project
"""

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
import datetime
import uuid
from werkzeug.utils import secure_filename
from plate_detector import detect_number_plate
from vehicle_db import get_vehicle_by_plate, add_detection_record, get_detection_history, search_vehicles
from csv_manager import csv_manager

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Save uploaded file with unique filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return file_path, unique_filename
    return None, None

@app.route("/")
def index():
    """Serve the main application page"""
    return render_template("index.html")

@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route("/api/upload", methods=['POST'])
def upload_image():
    """
    Handle image upload and number plate detection
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Save uploaded file
        file_path, filename = save_uploaded_file(file)
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, BMP'
            }), 400

        # Detect number plate
        detection_result = detect_number_plate(file_path)
        
        # Prepare response
        response_data = {
            'success': True,
            'detection': detection_result,
            'filename': filename,
            'timestamp': datetime.datetime.now().isoformat()
        }

        # If plate detected, lookup vehicle info and add to detection history
        if (detection_result['number_plate'] and 
            detection_result['number_plate'] != 'No plate detected' and
            not detection_result['number_plate'].startswith('Error:')):
            
            # Lookup vehicle information
            vehicle_info = get_vehicle_by_plate(detection_result['number_plate'])
            response_data['vehicle_info'] = vehicle_info
            
            # Add to detection history in database
            add_detection_record(
                plate=detection_result['number_plate'],
                confidence=detection_result['confidence'],
                image_path=filename
            )
            
            # Add to CSV with enhanced information
            csv_manager.add_detection(
                number_plate=detection_result['number_plate'],
                confidence=detection_result['confidence'],
                vehicle_info=vehicle_info,
                image_filename=filename,
                status='Detected'
            )

        else:
            # Add failed detection to CSV
            csv_manager.add_detection(
                number_plate=detection_result['number_plate'],
                confidence=detection_result['confidence'],
                image_filename=filename,
                status='Failed'
            )

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route("/api/lookup", methods=['POST'])
def lookup_vehicle():
    """
    Lookup vehicle information by plate number
    """
    try:
        data = request.get_json() or {}
        plate = (data.get('plate') or '').strip().upper()
        
        if not plate:
            return jsonify({
                'success': False,
                'error': 'No plate number provided'
            }), 400

        vehicle = get_vehicle_by_plate(plate)
        
        return jsonify({
            'success': True,
            'found': vehicle is not None,
            'vehicle': vehicle
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route("/api/history")
def get_history():
    """
    Get detection history from database
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        history = get_detection_history(limit=limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'total': len(history)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route("/api/search")
def search_vehicles_route():
    """
    Search vehicles by plate, owner, or model
    """
    try:
        search_term = request.args.get('q', '').strip()
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'No search term provided'
            }), 400

        results = search_vehicles(search_term)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route("/api/vehicle", methods=['POST'])
def add_vehicle_route():
    """
    Add or update vehicle information
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        if not data.get('plate') or not data.get('owner_name'):
            return jsonify({
                'success': False,
                'error': 'Plate number and owner name are required'
            }), 400

        from vehicle_db import add_vehicle
        add_vehicle(data)
        
        return jsonify({
            'success': True,
            'message': 'Vehicle information saved successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# CSV Management Endpoints
@app.route("/api/csv/stats")
def get_csv_stats():
    """Get CSV detection statistics"""
    try:
        stats = csv_manager.get_detection_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting stats: {str(e)}'
        }), 500

@app.route("/api/csv/search")
def search_csv_detections():
    """Search detections in CSV"""
    try:
        plate_number = request.args.get('plate', '')
        date = request.args.get('date', '')
        owner_name = request.args.get('owner', '')
        limit = request.args.get('limit', 50, type=int)
        
        results = csv_manager.search_detections(
            plate_number=plate_number,
            date=date,
            owner_name=owner_name,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error searching: {str(e)}'
        }), 500

@app.route("/api/csv/export")
def export_csv():
    """Export CSV data"""
    try:
        success, output_file = csv_manager.export_to_excel()
        
        if success and os.path.exists(output_file):
            return jsonify({
                'success': True,
                'message': f'Data exported to {output_file}',
                'filename': output_file
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Export failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Export error: {str(e)}'
        }), 500

@app.route("/api/csv/download/<filename>")
def download_csv(filename):
    """Download exported CSV file"""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Download error: {str(e)}'
        }), 500

@app.route("/api/csv/recent")
def get_recent_csv_detections():
    """Get recent detections from CSV"""
    try:
        limit = request.args.get('limit', 50, type=int)
        detections = csv_manager.get_recent_detections(limit=limit)
        
        return jsonify({
            'success': True,
            'detections': detections,
            'total': len(detections)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting recent detections: {str(e)}'
        }), 500

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'success': False,
        'error': 'File too large. Maximum size is 16MB.'
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == "__main__":
    print("Starting ANPR Server...")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print("Server running on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)