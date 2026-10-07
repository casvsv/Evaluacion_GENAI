import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURACIÓN ORIENTADA A PRODUCCIÓN ---
app.config['SECRET_KEY'] = 'cambia-esta-clave-en-produccion-por-una-variable-de-entorno'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

# Seguridad: Limitar tamaño máximo de subida a 5MB
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 

# Seguridad: Extensiones permitidas
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE BASE DE DATOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    files = db.relationship('UploadedFile', backref='owner', lazy=True)

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- UTILIDADES ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

# --- RUTAS ---
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    ensure_upload_folder()
    
    if request.method == 'POST':
        # Verificar si la petición tiene la parte del archivo
        if 'document' not in request.files:
            flash('No se encontró ninguna parte de archivo en la petición.', 'danger')
            return redirect(request.url)
            
        file = request.files['document']
        
        # Si el usuario no selecciona archivo, el navegador envía un archivo vacío sin nombre
        if file.filename == '':
            flash('No seleccionaste ningún archivo.', 'warning')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # Sanear el nombre del archivo para evitar ataques de Path Traversal
            original_filename = secure_filename(file.filename)
            
            # Generar un nombre único para evitar colisiones en el disco
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Guardar en disco
            file.save(filepath)
            
            # Guardar registro en Base de Datos asociado al usuario
            new_file_record = UploadedFile(
                filename=unique_filename,
                original_filename=original_filename,
                user_id=current_user.id
            )
            db.session.add(new_file_record)
            db.session.commit()
            
            flash('¡Archivo subido exitosamente!', 'success')
            return redirect(url_for('upload_file'))
        else:
            flash(f'Tipo de archivo no permitido. Solo se aceptan: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
            return redirect(request.url)
            
    # Obtener historial de archivos del usuario para mostrar en la vista
    user_files = UploadedFile.query.filter_by(user_id=current_user.id).all()
    return render_template('upload.html', files=user_files)

# --- RUTA DE CONFIGURACIÓN INICIAL (Para fines de prueba) ---
@app.route('/setup')
def setup():
    """Crea la BD e inicia sesión automáticamente con un usuario de prueba."""
    db.create_all()
    if not User.query.filter_by(username='usuario_demo').first():
        demo_user = User(username='usuario_demo')
        db.session.add(demo_user)
        db.session.commit()
    
    user = User.query.filter_by(username='usuario_demo').first()
    login_user(user)
    return redirect(url_for('upload_file'))

if __name__ == '__main__':
    # Ejecutar solo en desarrollo. En producción, usa Gunicorn.
    with app.app_context():
        db.create_all()
    app.run(debug=True)