from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, get_flashed_messages, send_file
import json
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages
ENDPOINTS_FILE = 'endpoints.json'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'json'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load existing endpoints from file
if os.path.exists(ENDPOINTS_FILE):
    with open(ENDPOINTS_FILE, 'r') as f:
        endpoints = json.load(f)
else:
    endpoints = {}

def save_endpoints():
    with open(ENDPOINTS_FILE, 'w') as f:
        json.dump(endpoints, f, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Pass flashed messages to the template
    messages = get_flashed_messages(with_categories=True)
    return render_template('index.html', endpoints=endpoints, messages=messages)

@app.route('/create', methods=['POST'])
def create_endpoint():
    endpoint_name = request.form['endpoint_name'].strip()
    json_data = request.form['json_data'].strip()

    # Replace spaces with underscores
    endpoint_name = endpoint_name.replace(' ', '_')

    # Validate endpoint name
    if not endpoint_name:
        flash('Endpoint name cannot be empty!', 'error')
        return redirect(url_for('index'))
    if '/' in endpoint_name:
        flash('Endpoint name cannot contain slashes!', 'error')
        return redirect(url_for('index'))
    if endpoint_name in endpoints:
        flash('Endpoint name already exists!', 'error')
        return redirect(url_for('index'))

    # Validate JSON data
    try:
        parsed_json = json.loads(json_data)
    except json.JSONDecodeError:
        flash('Invalid JSON format!', 'error')
        return redirect(url_for('index'))

    # Save the new endpoint with a counter and creation timestamp
    endpoints[endpoint_name] = {
        'data': parsed_json,
        'count': 0,  # Initialize counter
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Add creation timestamp
    }
    save_endpoints()
    flash(f'Endpoint "{endpoint_name}" created successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/api/create', methods=['POST'])
def api_create_endpoint():
    # Parse JSON payload
    try:
        payload = request.get_json()
        if not payload or 'endpoint_name' not in payload or 'json_data' not in payload:
            return jsonify({'error': 'Invalid payload. Must include "endpoint_name" and "json_data".'}), 400

        endpoint_name = payload['endpoint_name'].strip()
        json_data = payload['json_data']

        # Replace spaces with underscores
        endpoint_name = endpoint_name.replace(' ', '_')

        # Validate endpoint name
        if not endpoint_name:
            return jsonify({'error': 'Endpoint name cannot be empty!'}), 400
        if '/' in endpoint_name:
            return jsonify({'error': 'Endpoint name cannot contain slashes!'}), 400
        if endpoint_name in endpoints:
            return jsonify({'error': 'Endpoint name already exists!'}), 400

        # Validate JSON data
        try:
            parsed_json = json.loads(json_data) if isinstance(json_data, str) else json_data
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format!'}), 400

        # Save the new endpoint with a counter and creation timestamp
        endpoints[endpoint_name] = {
            'data': parsed_json,
            'count': 0,  # Initialize counter
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Add creation timestamp
        }
        save_endpoints()
        return jsonify({'message': f'Endpoint "{endpoint_name}" created successfully!'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/edit/<endpoint_name>', methods=['GET', 'POST'])
def edit_endpoint(endpoint_name):
    if endpoint_name not in endpoints:
        flash('Endpoint not found!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_json_data = request.form['json_data'].strip()

        # Validate JSON data
        try:
            parsed_json = json.loads(new_json_data)
        except json.JSONDecodeError:
            flash('Invalid JSON format!', 'error')
            return redirect(url_for('edit_endpoint', endpoint_name=endpoint_name))

        # Update the endpoint data (preserve the counter and creation timestamp)
        endpoints[endpoint_name]['data'] = parsed_json
        save_endpoints()
        flash(f'Endpoint "{endpoint_name}" updated successfully!', 'success')
        return redirect(url_for('index'))

    # Pre-fill the form with existing data
    return render_template('edit.html', endpoint_name=endpoint_name, json_data=json.dumps(endpoints[endpoint_name]['data'], indent=2))

@app.route('/delete/<endpoint_name>', methods=['POST'])
def delete_endpoint(endpoint_name):
    if endpoint_name in endpoints:
        del endpoints[endpoint_name]
        save_endpoints()
        flash(f'Endpoint "{endpoint_name}" deleted successfully!', 'success')
    else:
        flash('Endpoint not found!', 'error')
    return redirect(url_for('index'))

@app.route('/<endpoint_name>')
def serve_endpoint(endpoint_name):
    if endpoint_name in endpoints:
        # Increment the counter
        endpoints[endpoint_name]['count'] += 1
        save_endpoints()
        return jsonify(endpoints[endpoint_name]['data'])
    return "Endpoint not found", 404

@app.route('/export')
def export_endpoints():
    # Create a temporary file for export
    export_file = os.path.join(UPLOAD_FOLDER, 'endpoints_export.json')
    with open(export_file, 'w') as f:
        json.dump(endpoints, f, indent=2)
    return send_file(export_file, as_attachment=True, download_name='endpoints_export.json')

@app.route('/import', methods=['POST'])
def import_endpoints():
    if 'file' not in request.files:
        flash('No file uploaded!', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            with open(filepath, 'r') as f:
                imported_endpoints = json.load(f)

            # Merge imported endpoints with existing ones
            for endpoint_name, data in imported_endpoints.items():
                if endpoint_name not in endpoints:
                    data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Add creation timestamp for new endpoints
            endpoints.update(imported_endpoints)
            save_endpoints()
            flash('Endpoints imported successfully!', 'success')
        except json.JSONDecodeError:
            flash('Invalid JSON file!', 'error')
        finally:
            os.remove(filepath)  # Clean up the uploaded file
    else:
        flash('Only JSON files are allowed!', 'error')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)