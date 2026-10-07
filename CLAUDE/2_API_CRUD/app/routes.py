from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Empleado

bp = Blueprint('main', __name__)

# ==========================================
# RUTAS DE INTERFAZ WEB (UI)
# ==========================================

@bp.route('/')
def index():
    empleados = Empleado.query.all()
    return render_template('index.html', empleados=empleados)

@bp.route('/empleado/nuevo', methods=['GET', 'POST'])
def crear_empleado():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        cargo = request.form.get('cargo')
        salario = request.form.get('salario')
        
        nuevo_empleado = Empleado(nombre=nombre, cargo=cargo, salario=float(salario))
        db.session.add(nuevo_empleado)
        db.session.commit()
        
        flash('Empleado creado exitosamente.', 'success')
        return redirect(url_for('main.index'))
    return render_template('formulario.html', empleado=None)

@bp.route('/empleado/<int:id>/editar', methods=['GET', 'POST'])
def editar_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    if request.method == 'POST':
        empleado.nombre = request.form.get('nombre')
        empleado.cargo = request.form.get('cargo')
        empleado.salario = float(request.form.get('salario'))
        
        db.session.commit()
        flash('Datos del empleado actualizados.', 'info')
        return redirect(url_for('main.index'))
    return render_template('formulario.html', empleado=empleado)

@bp.route('/empleado/<int:id>/eliminar', methods=['POST'])
def eliminar_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    db.session.delete(empleado)
    db.session.commit()
    flash('Empleado eliminado del sistema.', 'danger')
    return redirect(url_for('main.index'))

# ==========================================
# RUTAS API REST (JSON)
# ==========================================

@bp.route('/api/empleados', methods=['GET'])
def api_get_empleados():
    empleados = Empleado.query.all()
    return jsonify([e.to_dict() for e in empleados]), 200

@bp.route('/api/empleados/<int:id>', methods=['GET'])
def api_get_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    return jsonify(empleado.to_dict()), 200

@bp.route('/api/empleados', methods=['POST'])
def api_create_empleado():
    data = request.get_json()
    if not data or not 'nombre' in data or not 'cargo' in data or not 'salario' in data:
        return jsonify({'error': 'Faltan datos requeridos'}), 400
    
    nuevo_empleado = Empleado(
        nombre=data['nombre'], 
        cargo=data['cargo'], 
        salario=float(data['salario'])
    )
    db.session.add(nuevo_empleado)
    db.session.commit()
    return jsonify(nuevo_empleado.to_dict()), 201

@bp.route('/api/empleados/<int:id>', methods=['PUT'])
def api_update_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    data = request.get_json()
    
    empleado.nombre = data.get('nombre', empleado.nombre)
    empleado.cargo = data.get('cargo', empleado.cargo)
    empleado.salario = data.get('salario', empleado.salario)
    
    db.session.commit()
    return jsonify(empleado.to_dict()), 200

@bp.route('/api/empleados/<int:id>', methods=['DELETE'])
def api_delete_empleado(id):
    empleado = Empleado.query.get_or_404(id)
    db.session.delete(empleado)
    db.session.commit()
    return jsonify({'mensaje': 'Empleado eliminado'}), 200