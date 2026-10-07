from app import create_app

app = create_app()

if __name__ == '__main__':
    # debug=True solo para desarrollo. En producción usar gunicorn o uwsgi
    app.run(debug=True, host='0.0.0.0', port=5000)