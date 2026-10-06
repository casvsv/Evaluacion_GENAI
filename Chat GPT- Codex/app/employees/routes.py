from flask import Blueprint, abort, jsonify, flash, redirect, render_template, request, url_for

from app.db import get_db, utc_now
from app.security import login_required, require_json

employees_bp = Blueprint("employees", __name__, url_prefix="/employees")
employees_api_bp = Blueprint("employees_api", __name__, url_prefix="/api/employees")


def validate_employee_payload(data):
    errors = {}
    name = str(data.get("name", "")).strip()
    position = str(data.get("position", "")).strip()
    salary_raw = data.get("salary", "")

    try:
        salary = float(salary_raw)
    except (TypeError, ValueError):
        salary = None
        errors["salary"] = "El salario debe ser numerico."

    if not name:
        errors["name"] = "El nombre es obligatorio."
    if not position:
        errors["position"] = "El cargo es obligatorio."
    if salary is not None and salary < 0:
        errors["salary"] = "El salario no puede ser negativo."

    return {"name": name, "position": position, "salary": salary}, errors


def find_employee_or_404(employee_id):
    employee = get_db().execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if employee is None:
        abort(404)
    return employee


@employees_bp.route("/")
@login_required
def list_employees():
    search_id = request.args.get("id", "").strip()
    db = get_db()
    employee = None
    employees = []

    if search_id:
        if search_id.isdigit():
            employee = db.execute("SELECT * FROM employees WHERE id = ?", (int(search_id),)).fetchone()
        else:
            flash("El ID debe ser numerico.", "warning")
    else:
        employees = db.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()

    return render_template("employees/list.html", employees=employees, employee=employee, search_id=search_id)


@employees_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_employee():
    if request.method == "POST":
        payload, errors = validate_employee_payload(request.form)
        if errors:
            for message in errors.values():
                flash(message, "danger")
        else:
            now = utc_now()
            db = get_db()
            db.execute(
                "INSERT INTO employees (name, position, salary, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (payload["name"], payload["position"], payload["salary"], now, now),
            )
            db.commit()
            flash("Empleado creado correctamente.", "success")
            return redirect(url_for("employees.list_employees"))

    return render_template("employees/form.html", employee=None, action="Crear")


@employees_bp.route("/<int:employee_id>")
@login_required
def show_employee(employee_id):
    return render_template("employees/detail.html", employee=find_employee_or_404(employee_id))


@employees_bp.route("/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
def edit_employee(employee_id):
    employee = find_employee_or_404(employee_id)

    if request.method == "POST":
        payload, errors = validate_employee_payload(request.form)
        if errors:
            for message in errors.values():
                flash(message, "danger")
        else:
            db = get_db()
            db.execute(
                "UPDATE employees SET name = ?, position = ?, salary = ?, updated_at = ? WHERE id = ?",
                (payload["name"], payload["position"], payload["salary"], utc_now(), employee_id),
            )
            db.commit()
            flash("Empleado actualizado correctamente.", "success")
            return redirect(url_for("employees.show_employee", employee_id=employee_id))

    return render_template("employees/form.html", employee=employee, action="Actualizar")


@employees_bp.route("/<int:employee_id>/delete", methods=["POST"])
@login_required
def delete_employee(employee_id):
    find_employee_or_404(employee_id)
    db = get_db()
    db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    db.commit()
    flash("Empleado eliminado.", "info")
    return redirect(url_for("employees.list_employees"))


@employees_bp.route("/api", methods=["GET", "POST"])
@employees_api_bp.route("", methods=["GET", "POST"])
def employees_api_collection():
    db = get_db()

    if request.method == "POST":
        require_json()
        payload, errors = validate_employee_payload(request.get_json() or {})
        if errors:
            return jsonify({"errors": errors}), 400

        now = utc_now()
        cursor = db.execute(
            "INSERT INTO employees (name, position, salary, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (payload["name"], payload["position"], payload["salary"], now, now),
        )
        db.commit()
        employee = db.execute("SELECT * FROM employees WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(dict(employee)), 201

    employees = db.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()
    return jsonify([dict(employee) for employee in employees])


@employees_bp.route("/api/<int:employee_id>", methods=["GET", "PUT", "DELETE"])
@employees_api_bp.route("/<int:employee_id>", methods=["GET", "PUT", "DELETE"])
def employees_api_item(employee_id):
    db = get_db()
    employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if employee is None:
        return jsonify({"error": "Empleado no encontrado."}), 404

    if request.method == "GET":
        return jsonify(dict(employee))

    if request.method == "DELETE":
        db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        db.commit()
        return jsonify({"message": "Empleado eliminado."})

    require_json()
    payload, errors = validate_employee_payload(request.get_json() or {})
    if errors:
        return jsonify({"errors": errors}), 400

    db.execute(
        "UPDATE employees SET name = ?, position = ?, salary = ?, updated_at = ? WHERE id = ?",
        (payload["name"], payload["position"], payload["salary"], utc_now(), employee_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    return jsonify(dict(updated))
