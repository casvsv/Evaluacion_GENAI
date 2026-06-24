import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(form_file):
    if form_file and allowed_file(form_file.filename):
        original_filename = secure_filename(form_file.filename)
        # Generate unique filename to prevent collisions and directory traversal
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        form_file.save(filepath)
        
        return unique_filename, original_filename
    return None, None
