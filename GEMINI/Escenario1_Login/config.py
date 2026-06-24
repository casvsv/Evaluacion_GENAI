import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Clave secreta para manejo de sesiones y tokens seguros
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura-para-dev'
    
    # Configuración de base de datos SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
