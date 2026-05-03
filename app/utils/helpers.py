import os
import uuid
import logging
from flask import current_app
import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_image(file):
    if file and allowed_file(file.filename):
        if current_app.config.get('CLOUDINARY_URL'):
            try:
                cloudinary.config(cloudinary_url=current_app.config['CLOUDINARY_URL'])
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="al_is_sweet_recipes",
                    allowed_formats=['jpg', 'png', 'jpeg', 'webp'],
                    transformation=[{'width': 1000, 'crop': "limit"}]
                )
                return upload_result.get('secure_url')
            except Exception as e:
                logger.error(f"Erreur Upload Cloudinary: {e}")
                return None
        else:
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return filename
    return None


def safe_int(val, default=0, min_val=0, max_val=9999):
    try:
        if val is None or val == '': return default
        return max(min_val, min(max_val, int(val)))
    except (TypeError, ValueError):
        return default


def safe_float(val, default=0.0, min_val=0.0, max_val=9999.0):
    try:
        if val is None or val == '': return default
        return max(min_val, min(max_val, float(val)))
    except (TypeError, ValueError):
        return default


def safe_str(val, max_length=None):
    if val is None: return None
    s = str(val).strip()
    return s[:max_length] if max_length else s
