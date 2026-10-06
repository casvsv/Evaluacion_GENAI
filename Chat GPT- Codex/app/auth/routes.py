import sqlite3
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.db import get_db, utc_now
from app.security import (
    current_user,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.app_context_processor
def inject_user():
    return {"current_user": current_user()}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not password:
            flash("Correo y contrasena son obligatorios.", "danger")
        elif len(password) < 8:
            flash("La contrasena debe tener al menos 8 caracteres.", "danger")
        elif password != confirm_password:
            flash("Las contrasenas no coinciden.", "danger")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                    (email, hash_password(password), utc_now()),
                )
                db.commit()
                flash("Cuenta creada. Ahora puedes iniciar sesion.", "success")
                return redirect(url_for("auth.login"))
            except sqlite3.IntegrityError:
                flash("Ya existe una cuenta con ese correo.", "danger")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not verify_password(user["password_hash"], password):
            flash("Credenciales invalidas.", "danger")
        else:
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            flash("Sesion iniciada correctamente.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("employees.list_employees"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesion cerrada.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/password/forgot", methods=["GET", "POST"])
def forgot_password():
    simulated_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_db().execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()

        if user is not None:
            token = generate_reset_token(user["id"])
            simulated_link = url_for("auth.reset_password", token=token, _external=True)
            print(f"[SIMULATED EMAIL] Password reset for {user['email']}: {simulated_link}")

        flash("Si el correo existe, se genero un enlace de recuperacion.", "info")

    return render_template("auth/forgot_password.html", simulated_link=simulated_link)


@auth_bp.route("/password/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = hash_token(token)
    reset = get_db().execute(
        """
        SELECT pr.*, u.email
        FROM password_resets pr
        JOIN users u ON u.id = pr.user_id
        WHERE pr.token_hash = ? AND pr.used = 0
        """,
        (token_hash,),
    ).fetchone()

    if reset is None:
        flash("El enlace de recuperacion no existe o ya fue usado.", "danger")
        return redirect(url_for("auth.forgot_password"))

    expires_at = datetime.fromisoformat(reset["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        flash("El enlace de recuperacion expiro.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("La nueva contrasena debe tener al menos 8 caracteres.", "danger")
        elif password != confirm_password:
            flash("Las contrasenas no coinciden.", "danger")
        else:
            db = get_db()
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), reset["user_id"]))
            db.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset["id"],))
            db.commit()
            flash("Contrasena actualizada. Inicia sesion con tu nueva clave.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", email=reset["email"])
