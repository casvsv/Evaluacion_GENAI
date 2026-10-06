import io
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from config import Config


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"


def csrf_from(response):
    match = re.search(r'name="_csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match, "No CSRF token found in form"
    return match.group(1)


def test_main_user_employee_and_upload_flow():
    with tempfile.TemporaryDirectory() as temp_dir:
        TestConfig.DATABASE = str(Path(temp_dir) / "test.sqlite3")
        TestConfig.UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")

        app = create_app(TestConfig)
        client = app.test_client()

        response = client.get("/auth/register")
        assert response.status_code == 200
        csrf = csrf_from(response)

        response = client.post(
            "/auth/register",
            data={
                "_csrf_token": csrf,
                "email": "ana@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        response = client.get("/auth/login")
        csrf = csrf_from(response)
        response = client.post(
            "/auth/login",
            data={"_csrf_token": csrf, "email": "ana@example.com", "password": "password123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Empleados" in response.data

        response = client.post(
            "/api/employees",
            json={"name": "Ana Ruiz", "position": "Backend Engineer", "salary": 2500},
        )
        assert response.status_code == 201
        employee_id = response.get_json()["id"]

        response = client.get(f"/api/employees/{employee_id}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Ana Ruiz"

        response = client.get("/uploads/")
        csrf = csrf_from(response)
        response = client.post(
            "/uploads/",
            data={
                "_csrf_token": csrf,
                "file": (io.BytesIO(b"%PDF-1.4 test"), "cv.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"cv.pdf" in response.data


if __name__ == "__main__":
    test_main_user_employee_and_upload_flow()
    print("smoke test ok")
