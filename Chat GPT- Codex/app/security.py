import functools
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import abort, flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db, utc_now


def hash_password(password):
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_reset_token(user_id):
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(timespec="seconds")

    db = get_db()
    db.execute(
        "INSERT INTO password_resets (user_id, token_hash, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
        (user_id, token_hash, expires_at, utc_now()),
    )
    db.commit()
    return token


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Debes iniciar sesion para continuar.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)

    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return get_db().execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()


def require_json():
    if not request.is_json:
        abort(415, description="La peticion debe usar application/json.")


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or request.is_json:
        return

    sent_token = request.form.get("_csrf_token")
    stored_token = session.get("_csrf_token")
    if not stored_token or not sent_token or not secrets.compare_digest(stored_token, sent_token):
        abort(400, description="Token CSRF invalido.")
