import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import assert_user_has_role
from app.core.security import verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def register_student(client: TestClient, email: str = "student@example.edu") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Test Student",
            "password": "correct-horse-battery-7",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_register_creates_student_and_never_returns_password_hash(client: TestClient) -> None:
    user = register_student(client)

    assert user["email"] == "student@example.edu"
    assert user["role"] == UserRole.STUDENT.value
    assert user["is_active"] is True
    assert "password" not in user
    assert "password_hash" not in user


def test_registration_rejects_self_assigned_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@example.edu",
            "full_name": "Test User",
            "password": "correct-horse-battery-7",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_login_and_authenticated_profile(client: TestClient) -> None:
    register_student(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "STUDENT@example.edu", "password": "correct-horse-battery-7"},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "student@example.edu"
    assert profile.json()["role"] == "student"


def test_password_is_stored_as_a_hash(client: TestClient) -> None:
    register_student(client)
    with TestClient(app) as test_client:
        token_response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "student@example.edu", "password": "correct-horse-battery-7"},
        )
    assert token_response.status_code == 200


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    register_student(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "STUDENT@example.edu",
            "full_name": "Another Student",
            "password": "different-secure-password",
        },
    )

    assert response.status_code == 409


def test_wrong_password_is_rejected(client: TestClient) -> None:
    register_student(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.edu", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_profile_requires_a_valid_bearer_token(client: TestClient) -> None:
    no_token = client.get("/api/v1/auth/me")
    invalid_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert no_token.status_code == 401
    assert invalid_token.status_code == 401


def test_role_guard_rejects_a_student_from_instructor_only_access() -> None:
    student = User(
        id=1,
        email="student@example.edu",
        full_name="Test Student",
        password_hash="not-used-in-this-test",
        role=UserRole.STUDENT.value,
        is_active=True,
    )

    with pytest.raises(HTTPException) as error:
        assert_user_has_role(student, UserRole.INSTRUCTOR, UserRole.ADMIN)

    assert error.value.status_code == 403


def test_role_guard_accepts_an_instructor() -> None:
    instructor = User(
        id=2,
        email="instructor@example.edu",
        full_name="Test Instructor",
        password_hash="not-used-in-this-test",
        role=UserRole.INSTRUCTOR.value,
        is_active=True,
    )

    assert assert_user_has_role(instructor, UserRole.INSTRUCTOR) is instructor
