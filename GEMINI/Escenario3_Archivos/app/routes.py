import os
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
