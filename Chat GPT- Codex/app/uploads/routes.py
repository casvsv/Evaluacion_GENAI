import secrets
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from app.db import get_db, utc_now
from app.security import login_required

uploads_bp = Blueprint("uploads", __name__, url_prefix="/uploads")


def allowed_file(filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return extension in current_app.config["ALLOWED_EXTENSIONS"]


@uploads_bp.route("/", methods=["GET", "POST"])
@login_required
def upload_file():
    if request.method == "POST":
        uploaded_file = request.files.get("file")

        if uploaded_file is None or uploaded_file.filename == "":
            flash("Selecciona un archivo.", "danger")
        elif not allowed_file(uploaded_file.filename):
            flash("Formato no permitido. Usa PDF, PNG, JPG o JPEG.", "danger")
        else:
            original_filename = secure_filename(uploaded_file.filename)
            extension = original_filename.rsplit(".", 1)[-1].lower()
            stored_filename = f"{session['user_id']}_{secrets.token_hex(12)}.{extension}"
            destination = Path(current_app.config["UPLOAD_FOLDER"]) / stored_filename
            uploaded_file.save(destination)
            size_bytes = destination.stat().st_size

            db = get_db()
            db.execute(
                """
                INSERT INTO user_files
                    (user_id, stored_filename, original_filename, content_type, size_bytes, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    stored_filename,
                    original_filename,
                    uploaded_file.content_type,
                    size_bytes,
                    utc_now(),
                ),
            )
            db.commit()
            flash("Archivo subido correctamente.", "success")
            return redirect(url_for("uploads.upload_file"))

    files = get_db().execute(
        "SELECT * FROM user_files WHERE user_id = ? ORDER BY uploaded_at DESC",
        (session.get("user_id"),),
    ).fetchall()
    return render_template("uploads/upload.html", files=files)
