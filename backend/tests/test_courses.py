import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture()
def context():
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
    with TestClient(app) as client:
        yield client, test_session
    app.dependency_overrides.clear()
    engine.dispose()


def add_user(test_session, email: str, role: UserRole) -> tuple[User, dict[str, str]]:
    with test_session() as db:
        user = User(
            email=email,
            full_name=email.split("@")[0].title(),
            password_hash="test-only-hash",
            role=role.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    token = create_access_token(str(user_id))
    return user, {"Authorization": f"Bearer {token}"}


def create_course(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "title": "Introduction to Networks",
            "description": "Networking fundamentals",
            "term": "Fall 2026",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_instructor_creates_course_and_student_enrolls(context) -> None:
    client, test_session = context
    _, instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    _, student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course = create_course(client, instructor_headers)

    assert course["enrollment_code"]
    assert "enrollment_code" not in client.get(
        f"/api/v1/courses/{course['id']}", headers=instructor_headers
    ).json()

    enrollment = client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json={"enrollment_code": course["enrollment_code"].lower()},
    )
    assert enrollment.status_code == 201
    assert enrollment.json()["course_id"] == course["id"]

    student_courses = client.get("/api/v1/courses", headers=student_headers)
    assert student_courses.status_code == 200
    assert [item["id"] for item in student_courses.json()] == [course["id"]]


def test_registration_role_boundary_and_course_creation_permissions(context) -> None:
    client, test_session = context
    _, student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)

    response = client.post(
        "/api/v1/courses",
        headers=student_headers,
        json={"title": "Not allowed"},
    )
    assert response.status_code == 403


def test_duplicate_enrollment_is_rejected(context) -> None:
    client, test_session = context
    _, instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    _, student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course = create_course(client, instructor_headers)
    payload = {"enrollment_code": course["enrollment_code"]}

    first_enrollment = client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json=payload,
    )
    assert first_enrollment.status_code == 201
    duplicate = client.post("/api/v1/courses/enroll", headers=student_headers, json=payload)
    assert duplicate.status_code == 409


def test_course_content_is_hidden_from_non_enrolled_students(context) -> None:
    client, test_session = context
    _, instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    _, student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course = create_course(client, instructor_headers)

    response = client.get(f"/api/v1/courses/{course['id']}", headers=student_headers)
    assert response.status_code == 403


def test_topic_question_bank_and_student_permission_boundary(context) -> None:
    client, test_session = context
    _, instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    _, student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course = create_course(client, instructor_headers)

    topic_response = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        headers=instructor_headers,
        json={"title": "IP addressing", "description": "IPv4 and subnet masks", "sort_order": 1},
    )
    assert topic_response.status_code == 201, topic_response.text
    topic = topic_response.json()

    question_response = client.post(
        f"/api/v1/courses/{course['id']}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic["id"],
            "prompt": "Which layer routes IP packets?",
            "explanation": "Routing is a network-layer function.",
            "difficulty": "medium",
            "options": [
                {"text": "Application", "is_correct": False},
                {"text": "Network", "is_correct": True},
                {"text": "Physical", "is_correct": False},
            ],
        },
    )
    assert question_response.status_code == 201, question_response.text
    question = question_response.json()
    assert sum(option["is_correct"] for option in question["options"]) == 1

    list_response = client.get(
        f"/api/v1/courses/{course['id']}/questions?topic_id={topic['id']}",
        headers=instructor_headers,
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    blocked = client.get(
        f"/api/v1/courses/{course['id']}/questions",
        headers=student_headers,
    )
    assert blocked.status_code == 403


def test_topic_cannot_be_deleted_while_questions_reference_it(context) -> None:
    client, test_session = context
    _, instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    course = create_course(client, instructor_headers)
    topic = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        headers=instructor_headers,
        json={"title": "Routing"},
    ).json()

    client.post(
        f"/api/v1/courses/{course['id']}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic["id"],
            "prompt": "What does a router do?",
            "options": [
                {"text": "Forward packets", "is_correct": True},
                {"text": "Compile source code", "is_correct": False},
            ],
        },
    )
    response = client.delete(
        f"/api/v1/courses/{course['id']}/topics/{topic['id']}",
        headers=instructor_headers,
    )
    assert response.status_code == 409


def test_question_requires_exactly_one_correct_option(context) -> None:
    client, test_session = context
    _, instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    course = create_course(client, instructor_headers)
    topic = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        headers=instructor_headers,
        json={"title": "Switching"},
    ).json()

    response = client.post(
        f"/api/v1/courses/{course['id']}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic["id"],
            "prompt": "Which item is correct?",
            "options": [
                {"text": "Option A", "is_correct": True},
                {"text": "Option B", "is_correct": True},
            ],
        },
    )
    assert response.status_code == 422


def test_instructor_cannot_manage_another_instructors_course(context) -> None:
    client, test_session = context
    _, owner_headers = add_user(test_session, "owner@example.edu", UserRole.INSTRUCTOR)
    _, other_headers = add_user(test_session, "other@example.edu", UserRole.INSTRUCTOR)
    course = create_course(client, owner_headers)

    response = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        headers=other_headers,
        json={"title": "Unauthorized topic"},
    )
    assert response.status_code == 403
