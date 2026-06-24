import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = os.path.abspath(os.path.dirname(__file__))

files = {
    "requirements.txt": """Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Bcrypt==1.0.1
Werkzeug==3.0.3
python-dotenv==1.0.1
""",

    "config.py": """import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una_clave_muy_secreta_y_segura_para_produccion_2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \\
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de subida de archivos
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB max
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
""",

    "run.py": """from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
""",

    "app/__init__.py": """import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app
""",

    "app/models.py": """from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    files = db.relationship('UploadedFile', backref='owner', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"UploadedFile('{self.filename}', '{self.upload_date}')"
""",

    "app/utils.py": """import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    return '.' in filename and \\
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
""",

    "app/routes.py": """import os
from flask import Blueprint, render_template, url_for, flash, redirect, request, current_app, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User, UploadedFile
from app.utils import save_file, allowed_file

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', title='Inicio de Sesión')

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()
        
        if user_exists or username_exists:
            flash('El usuario o correo ya existe. Por favor inicia sesión.', 'danger')
            return redirect(url_for('main.register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Tu cuenta ha sido creada. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('register.html', title='Registro')

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Inicio de sesión fallido. Verifica tu email y contraseña.', 'danger')
            
    return render_template('login.html', title='Inicio de Sesión')

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route("/dashboard")
@login_required
def dashboard():
    files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.upload_date.desc()).all()
    return render_template('dashboard.html', title='Dashboard - Mis Archivos', files=files)

@main.route("/upload", methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(request.url)
        
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if file and allowed_file(file.filename):
        unique_filename, original_filename = save_file(file)
        if unique_filename:
            new_file = UploadedFile(filename=unique_filename, original_filename=original_filename, owner=current_user)
            db.session.add(new_file)
            db.session.commit()
            flash(f'El archivo {original_filename} se ha subido correctamente.', 'success')
        else:
            flash('Error al procesar el archivo.', 'danger')
    else:
        flash('Tipo de archivo no permitido. Solo se permiten: txt, pdf, png, jpg, jpeg, gif', 'danger')
        
    return redirect(url_for('main.dashboard'))

@main.route("/download/<filename>")
@login_required
def download_file(filename):
    file_record = UploadedFile.query.filter_by(filename=filename).first_or_404()
    # Verificar propiedad del archivo
    if file_record.owner != current_user:
        flash('No tienes permiso para descargar este archivo.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, download_name=file_record.original_filename)

@main.route("/delete/<int:file_id>", methods=['POST'])
@login_required
def delete_file(file_id):
    file_record = UploadedFile.query.get_or_404(file_id)
    if file_record.owner != current_user:
        flash('No tienes permiso para eliminar este archivo.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.filename))
    except FileNotFoundError:
        pass # Si ya no existe en disco, solo borrar de BD
        
    db.session.delete(file_record)
    db.session.commit()
    flash('El archivo ha sido eliminado.', 'info')
    return redirect(url_for('main.dashboard'))
""",

    "app/templates/base.html": """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Sistema Cloud</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                    },
                    colors: {
                        primary: {
                            50: '#eff6ff',
                            100: '#dbeafe',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8',
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-slate-900 text-white min-h-screen flex flex-col antialiased">
    <!-- Navbar -->
    <nav class="bg-slate-800/50 backdrop-blur-md border-b border-slate-700 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center">
                    <a href="{{ url_for('main.home') }}" class="flex items-center gap-2">
                        <div class="w-8 h-8 rounded bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center font-bold text-lg">
                            <i class="fa-solid fa-cloud"></i>
                        </div>
                        <span class="font-bold text-xl tracking-tight">CloudVault</span>
                    </a>
                </div>
                <div>
                    <div class="ml-4 flex items-center md:ml-6 gap-4">
                        {% if current_user.is_authenticated %}
                            <span class="text-sm text-slate-300">Hola, <span class="font-semibold text-white">{{ current_user.username }}</span></span>
                            <a href="{{ url_for('main.dashboard') }}" class="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors">Dashboard</a>
                            <a href="{{ url_for('main.logout') }}" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all">Salir</a>
                        {% else %}
                            <a href="{{ url_for('main.login') }}" class="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors">Entrar</a>
                            <a href="{{ url_for('main.register') }}" class="bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg shadow-primary-500/30 transition-all transform hover:-translate-y-0.5">Registrarse</a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8 relative">
        <!-- Decoraciones de fondo -->
        <div class="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl -z-10 animate-pulse-slow"></div>
        <div class="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl -z-10 animate-pulse-slow delay-1000"></div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="max-w-md mx-auto mb-6 flex flex-col gap-3">
                {% for category, message in messages %}
                    <div class="p-4 rounded-xl shadow-lg border backdrop-blur-sm animate-fade-in-down
                        {% if category == 'success' %} bg-emerald-500/10 border-emerald-500/20 text-emerald-400
                        {% elif category == 'danger' %} bg-red-500/10 border-red-500/20 text-red-400
                        {% elif category == 'info' %} bg-blue-500/10 border-blue-500/20 text-blue-400
                        {% else %} bg-slate-500/10 border-slate-500/20 text-slate-300 {% endif %}">
                        <div class="flex items-center gap-3">
                            <i class="fa-solid {% if category == 'success' %}fa-check-circle{% elif category == 'danger' %}fa-exclamation-circle{% elif category == 'info' %}fa-info-circle{% else %}fa-bell{% endif %}"></i>
                            <p class="text-sm font-medium">{{ message }}</p>
                        </div>
                    </div>
                {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-slate-900 border-t border-slate-800 py-6 mt-auto">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p class="text-slate-500 text-sm">&copy; 2026 CloudVault. Todos los derechos reservados.</p>
        </div>
    </footer>
    
    {% block scripts %}{% endblock %}
</body>
</html>
""",

    "app/templates/login.html": """{% extends "base.html" %}
{% block content %}
<div class="max-w-md mx-auto mt-10">
    <div class="bg-slate-800/60 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 p-8 transform transition-all hover:shadow-primary-500/10 relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-600 to-purple-600"></div>
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">Bienvenido de nuevo</h1>
            <p class="text-slate-400">Ingresa a tu cuenta para continuar</p>
        </div>
        
        <form method="POST" action="">
            <div class="space-y-5">
                <div>
                    <label class="block text-sm font-medium text-slate-300 mb-1" for="email">Correo Electrónico</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fa-regular fa-envelope text-slate-500"></i>
                        </div>
                        <input class="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all" id="email" name="email" type="email" required placeholder="tu@email.com">
                    </div>
                </div>
                
                <div>
                    <div class="flex justify-between items-center mb-1">
                        <label class="block text-sm font-medium text-slate-300" for="password">Contraseña</label>
                        <a href="#" class="text-xs text-primary-400 hover:text-primary-300">¿Olvidaste tu contraseña?</a>
                    </div>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fa-solid fa-lock text-slate-500"></i>
                        </div>
                        <input class="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all" id="password" name="password" type="password" required placeholder="••••••••">
                    </div>
                </div>
                
                <div class="flex items-center">
                    <input id="remember" name="remember" type="checkbox" class="h-4 w-4 bg-slate-900 border-slate-700 rounded text-primary-600 focus:ring-primary-500">
                    <label for="remember" class="ml-2 block text-sm text-slate-400">
                        Recordarme
                    </label>
                </div>
                
                <button type="submit" class="w-full bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-medium py-2.5 rounded-lg shadow-lg shadow-primary-500/25 transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-primary-500">
                    Iniciar Sesión
                </button>
            </div>
        </form>
        
        <p class="mt-6 text-center text-sm text-slate-400">
            ¿No tienes una cuenta? 
            <a href="{{ url_for('main.register') }}" class="font-medium text-primary-400 hover:text-primary-300 transition-colors">Regístrate</a>
        </p>
    </div>
</div>
{% endblock %}
""",

    "app/templates/register.html": """{% extends "base.html" %}
{% block content %}
<div class="max-w-md mx-auto mt-10">
    <div class="bg-slate-800/60 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 p-8 transform transition-all hover:shadow-primary-500/10 relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-600 to-purple-600"></div>
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">Crear Cuenta</h1>
            <p class="text-slate-400">Únete a CloudVault hoy mismo</p>
        </div>
        
        <form method="POST" action="">
            <div class="space-y-5">
                <div>
                    <label class="block text-sm font-medium text-slate-300 mb-1" for="username">Nombre de Usuario</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fa-regular fa-user text-slate-500"></i>
                        </div>
                        <input class="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all" id="username" name="username" type="text" required placeholder="johndoe">
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-slate-300 mb-1" for="email">Correo Electrónico</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fa-regular fa-envelope text-slate-500"></i>
                        </div>
                        <input class="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all" id="email" name="email" type="email" required placeholder="tu@email.com">
                    </div>
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-slate-300 mb-1" for="password">Contraseña</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fa-solid fa-lock text-slate-500"></i>
                        </div>
                        <input class="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all" id="password" name="password" type="password" required placeholder="••••••••">
                    </div>
                </div>
                
                <button type="submit" class="w-full bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 text-white font-medium py-2.5 rounded-lg shadow-lg shadow-primary-500/25 transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-primary-500">
                    Registrarse
                </button>
            </div>
        </form>
        
        <p class="mt-6 text-center text-sm text-slate-400">
            ¿Ya tienes una cuenta? 
            <a href="{{ url_for('main.login') }}" class="font-medium text-primary-400 hover:text-primary-300 transition-colors">Inicia sesión</a>
        </p>
    </div>
</div>
{% endblock %}
""",

    "app/templates/dashboard.html": """{% extends "base.html" %}
{% block content %}
<div class="max-w-6xl mx-auto mt-4">
    <div class="flex flex-col lg:flex-row gap-8">
        
        <!-- Panel de Subida -->
        <div class="lg:w-1/3">
            <div class="bg-slate-800/60 backdrop-blur-xl rounded-2xl shadow-xl border border-slate-700/50 p-6 sticky top-24">
                <h2 class="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <div class="w-8 h-8 rounded-lg bg-primary-500/20 text-primary-400 flex items-center justify-center">
                        <i class="fa-solid fa-cloud-arrow-up"></i>
                    </div>
                    Subir Archivo
                </h2>
                <p class="text-sm text-slate-400 mb-6">Sube tus documentos (PDF) o imágenes. Tamaño máximo 16MB.</p>
                
                <form action="{{ url_for('main.upload_file') }}" method="POST" enctype="multipart/form-data" class="space-y-4">
                    <div class="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center hover:border-primary-500 transition-colors bg-slate-900/30 group relative">
                        <input type="file" name="file" id="file-upload" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" required onchange="updateFileName(this)">
                        <div class="flex flex-col items-center justify-center space-y-3 pointer-events-none">
                            <div class="w-14 h-14 bg-slate-800 rounded-full flex items-center justify-center group-hover:bg-primary-500/20 group-hover:text-primary-400 transition-colors shadow-inner border border-slate-700">
                                <i class="fa-solid fa-file-arrow-up text-2xl text-slate-400 group-hover:text-primary-400"></i>
                            </div>
                            <div>
                                <p class="text-sm font-medium text-white group-hover:text-primary-400 transition-colors">Haz clic o arrastra un archivo</p>
                                <p class="text-xs text-slate-500 mt-1">Soporta: PDF, TXT, PNG, JPG</p>
                            </div>
                        </div>
                    </div>
                    <div id="file-name-display" class="hidden text-sm text-primary-300 bg-primary-500/10 px-3 py-2 rounded-lg border border-primary-500/20 break-all text-center font-medium">
                        <!-- El nombre del archivo se mostrará aquí -->
                    </div>
                    <button type="submit" class="w-full bg-white text-slate-900 hover:bg-slate-100 font-semibold py-2.5 rounded-lg shadow-lg transition-all transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-white flex justify-center items-center gap-2">
                        <i class="fa-solid fa-upload"></i> Subir al Servidor
                    </button>
                </form>
            </div>
        </div>

        <!-- Lista de Archivos -->
        <div class="lg:w-2/3">
            <div class="bg-slate-800/60 backdrop-blur-xl rounded-2xl shadow-xl border border-slate-700/50 p-6 min-h-[500px]">
                <div class="flex justify-between items-center mb-6 pb-4 border-b border-slate-700/50">
                    <h2 class="text-xl font-bold text-white flex items-center gap-2">
                        <div class="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center">
                            <i class="fa-regular fa-folder-open"></i>
                        </div>
                        Mis Documentos
                    </h2>
                    <span class="bg-slate-700 text-slate-300 text-xs font-medium px-3 py-1.5 rounded-full border border-slate-600">{{ files|length }} Archivos guardados</span>
                </div>

                {% if files %}
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {% for file in files %}
                        <div class="bg-slate-900/50 border border-slate-700 rounded-xl p-4 flex flex-col hover:border-slate-500 transition-colors group relative overflow-hidden">
                            <div class="absolute top-0 left-0 w-1 h-full 
                                {% if file.original_filename.endswith('.pdf') %} bg-red-500
                                {% elif file.original_filename.endswith('.png') or file.original_filename.endswith('.jpg') or file.original_filename.endswith('.jpeg') %} bg-blue-500
                                {% else %} bg-slate-500 {% endif %} opacity-50 group-hover:opacity-100 transition-opacity"></div>
                            
                            <div class="flex items-start justify-between mb-4 pl-2">
                                <div class="flex items-center gap-3 overflow-hidden">
                                    <div class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-inner
                                        {% if file.original_filename.endswith('.pdf') %} bg-red-500/10 text-red-400 border border-red-500/20
                                        {% elif file.original_filename.endswith('.png') or file.original_filename.endswith('.jpg') or file.original_filename.endswith('.jpeg') %} bg-blue-500/10 text-blue-400 border border-blue-500/20
                                        {% else %} bg-slate-800 text-slate-400 border border-slate-700 {% endif %}">
                                        {% if file.original_filename.endswith('.pdf') %}
                                            <i class="fa-solid fa-file-pdf text-xl"></i>
                                        {% elif file.original_filename.endswith('.png') or file.original_filename.endswith('.jpg') or file.original_filename.endswith('.jpeg') %}
                                            <i class="fa-regular fa-image text-xl"></i>
                                        {% else %}
                                            <i class="fa-regular fa-file-lines text-xl"></i>
                                        {% endif %}
                                    </div>
                                    <div class="overflow-hidden">
                                        <h3 class="text-sm font-semibold text-white truncate" title="{{ file.original_filename }}">{{ file.original_filename }}</h3>
                                        <p class="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                                            <i class="fa-regular fa-clock text-[10px]"></i> {{ file.upload_date.strftime('%d %b %Y, %H:%M') }}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div class="mt-auto pt-3 flex items-center justify-between border-t border-slate-700/50 pl-2">
                                <a href="{{ url_for('main.download_file', filename=file.filename) }}" class="text-xs font-medium text-slate-300 hover:text-primary-400 flex items-center gap-1.5 transition-colors bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700">
                                    <i class="fa-solid fa-download"></i> Descargar
                                </a>
                                <form action="{{ url_for('main.delete_file', file_id=file.id) }}" method="POST" class="inline" onsubmit="return confirm('¿Estás seguro de que deseas eliminar este archivo de forma permanente?');">
                                    <button type="submit" class="text-xs font-medium text-slate-400 hover:text-red-400 flex items-center gap-1.5 transition-colors p-1.5 rounded-lg hover:bg-red-500/10">
                                        <i class="fa-regular fa-trash-can"></i>
                                    </button>
                                </form>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="h-full flex flex-col items-center justify-center py-16 border-2 border-dashed border-slate-700 rounded-xl bg-slate-900/20">
                        <div class="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-5 text-slate-500 shadow-inner border border-slate-700">
                            <i class="fa-regular fa-folder-open text-3xl"></i>
                        </div>
                        <h3 class="text-xl font-medium text-white mb-2">Tu bóveda está vacía</h3>
                        <p class="text-slate-400 text-sm max-w-sm mx-auto text-center">Aún no has subido ningún archivo. Utiliza el panel de la izquierda para comenzar a subir documentos y mantenerlos seguros.</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    function updateFileName(input) {
        const display = document.getElementById('file-name-display');
        if (input.files && input.files.length > 0) {
            display.innerHTML = '<i class="fa-solid fa-check-circle mr-1"></i> ' + input.files[0].name;
            display.classList.remove('hidden');
        } else {
            display.classList.add('hidden');
        }
    }
</script>
{% endblock %}
""",

    "app/static/css/style.css": """/* Custom Animations and utilities */
@keyframes fadeInDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in-down {
    animation: fadeInDown 0.4s ease-out forwards;
}

@keyframes pulseSlow {
    0%, 100% {
        opacity: 0.2;
        transform: scale(1);
    }
    50% {
        opacity: 0.3;
        transform: scale(1.05);
    }
}

.animate-pulse-slow {
    animation: pulseSlow 8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.delay-1000 {
    animation-delay: 1s;
}

/* Scrollbar Styling for a premium feel */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #0f172a; 
}

::-webkit-scrollbar-thumb {
    background: #334155; 
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #475569; 
}
"""
}

for filename, content in files.items():
    filepath = os.path.join(base_dir, filename)
    create_file(filepath, content)

print("Project structure created successfully!")
