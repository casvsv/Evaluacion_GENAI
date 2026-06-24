from flask import Blueprint, render_template, url_for, flash, redirect, request
from app import db, bcrypt
from app.models import User
from flask_login import login_user, current_user, logout_user, login_required
from app.utils import send_reset_email

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('main.register'))
            
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('El correo ya está registrado. Por favor, inicia sesión.', 'warning')
            return redirect(url_for('main.register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('¡Tu cuenta ha sido creada exitosamente! Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('register.html', title='Registro')

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Inicio de sesión fallido. Por favor, verifica el correo y la contraseña.', 'danger')
            
    return render_template('login.html', title='Iniciar Sesión')

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            send_reset_email(user, token)
            flash('Se ha enviado un correo con instrucciones para restablecer tu contraseña. Revisa la consola del servidor.', 'info')
            return redirect(url_for('main.login'))
        else:
            # Mostramos el mismo mensaje para no revelar qué correos existen en BD (seguridad)
            flash('Si existe una cuenta con ese correo, se ha enviado un enlace para restablecer la contraseña.', 'info')
            return redirect(url_for('main.login'))
            
    return render_template('forgot_password.html', title='Recuperar Contraseña')

@main.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    user = User.verify_reset_token(token)
    if user is None:
        flash('El enlace es inválido o ha expirado.', 'warning')
        return redirect(url_for('main.reset_request'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('main.reset_token', token=token))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('¡Tu contraseña ha sido actualizada! Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('reset_password.html', title='Restablecer Contraseña')
