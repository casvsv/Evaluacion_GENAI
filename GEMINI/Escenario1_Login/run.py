from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Crea las tablas de la base de datos si no existen
        db.create_all()
    # Ejecuta la aplicación
    app.run(debug=True, host='0.0.0.0', port=5000)
