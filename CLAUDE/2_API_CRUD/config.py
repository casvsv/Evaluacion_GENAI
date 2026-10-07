import os

class Config:
    # En producción, asegúrate de definir SECRET_KEY como variable de entorno
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-muy-segura'
    # Base de datos SQLite por defecto, escalable a PostgreSQL/MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///empleados.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False