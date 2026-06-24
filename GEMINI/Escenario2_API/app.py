from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Employee
import os

app = Flask(__name__)

# Configurations
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'employees.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super-secret-key-for-production-ready-app'

# Initialize Database
db.init_app(app)

with app.app_context():
    db.create_all()

# --- WEB INTERFACE ROUTES ---

@app.route('/')
def index():
    query = request.args.get('q', '')
    if query:
        # Buscador por nombre o ID
        employees = Employee.query.filter(Employee.name.ilike(f'%{query}%') | Employee.id.like(f'{query}')).all()
    else:
        employees = Employee.query.all()
    return render_template('index.html', employees=employees, query=query)

@app.route('/employee/new', methods=['GET', 'POST'])
def create_employee():
    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        salary = request.form.get('salary')
        
        if not name or not position or not salary:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('create_employee'))
        
        try:
            salary = float(salary)
        except ValueError:
            flash('El salario debe ser un número válido.', 'error')
            return redirect(url_for('create_employee'))

        new_employee = Employee(name=name, position=position, salary=salary)
        db.session.add(new_employee)
        db.session.commit()
        
        flash('Empleado creado exitosamente.', 'success')
        return redirect(url_for('index'))
        
    return render_template('create.html')

@app.route('/employee/<int:id>')
def view_employee(id):
    employee = Employee.query.get_or_404(id)
    return render_template('detail.html', employee=employee)

@app.route('/employee/<int:id>/edit', methods=['GET', 'POST'])
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        salary = request.form.get('salary')
        
        if not name or not position or not salary:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('edit_employee', id=id))
            
        try:
            employee.salary = float(salary)
        except ValueError:
            flash('El salario debe ser un número válido.', 'error')
            return redirect(url_for('edit_employee', id=id))

        employee.name = name
        employee.position = position
        
        db.session.commit()
        flash('Empleado actualizado exitosamente.', 'success')
        return redirect(url_for('index'))
        
    return render_template('edit.html', employee=employee)

@app.route('/employee/<int:id>/delete', methods=['POST'])
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    flash('Empleado eliminado exitosamente.', 'success')
    return redirect(url_for('index'))


# --- API REST ENDPOINTS ---

@app.route('/api/employees', methods=['GET'])
def api_get_employees():
    employees = Employee.query.all()
    return jsonify([emp.to_dict() for emp in employees]), 200

@app.route('/api/employees/<int:id>', methods=['GET'])
def api_get_employee(id):
    employee = Employee.query.get_or_404(id)
    return jsonify(employee.to_dict()), 200

@app.route('/api/employees', methods=['POST'])
def api_create_employee():
    data = request.get_json()
    if not data or not 'name' in data or not 'position' in data or not 'salary' in data:
        return jsonify({'error': 'Faltan campos requeridos: name, position, salary'}), 400
        
    try:
        salary = float(data['salary'])
    except ValueError:
        return jsonify({'error': 'El salario debe ser un número válido'}), 400

    new_employee = Employee(name=data['name'], position=data['position'], salary=salary)
    db.session.add(new_employee)
    db.session.commit()
    
    return jsonify(new_employee.to_dict()), 201

@app.route('/api/employees/<int:id>', methods=['PUT'])
def api_update_employee(id):
    employee = Employee.query.get_or_404(id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No se proporcionaron datos para actualizar'}), 400

    if 'name' in data:
        employee.name = data['name']
    if 'position' in data:
        employee.position = data['position']
    if 'salary' in data:
        try:
            employee.salary = float(data['salary'])
        except ValueError:
            return jsonify({'error': 'El salario debe ser un número válido'}), 400
            
    db.session.commit()
    return jsonify(employee.to_dict()), 200

@app.route('/api/employees/<int:id>', methods=['DELETE'])
def api_delete_employee(id):
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    return jsonify({'message': 'Empleado eliminado exitosamente'}), 200

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Recurso no encontrado'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Error interno del servidor'}), 500
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
