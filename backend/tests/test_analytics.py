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


def add_user(test_session, email: str, role: UserRole) -> dict[str, str]:
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
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def create_question(
    client: TestClient,
    course_id: int,
    topic_id: int,
    prompt: str,
    correct_text: str,
    instructor_headers: dict[str, str],
) -> dict:
    response = client.post(
        f"/api/v1/courses/{course_id}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic_id,
            "prompt": prompt,
            "status": "published",
            "options": [
                {"text": "Incorrect choice", "is_correct": False},
                {"text": correct_text, "is_correct": True},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_course_analytics_aggregate_results_by_topic_and_student(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "teacher@example.edu", UserRole.INSTRUCTOR)
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)

    created_course = client.post(
        "/api/v1/courses",
        headers=instructor_headers,
        json={"title": "Discrete Mathematics"},
    )
    assert created_course.status_code == 201, created_course.text
    course = created_course.json()
    course_id = course["id"]

    first_topic = client.post(
        f"/api/v1/courses/{course_id}/topics",
        headers=instructor_headers,
        json={"title": "Graph theory", "sort_order": 1},
    )
    second_topic = client.post(
        f"/api/v1/courses/{course_id}/topics",
        headers=instructor_headers,
        json={"title": "Combinatorics", "sort_order": 2},
    )
    assert first_topic.status_code == 201, first_topic.text
    assert second_topic.status_code == 201, second_topic.text

    first_question = create_question(
        client,
        course_id,
        first_topic.json()["id"],
        "What is a tree graph?",
        "A connected acyclic graph",
        instructor_headers,
    )
    second_question = create_question(
        client,
        course_id,
        second_topic.json()["id"],
        "What counts combinations?",
        "Selection groups",
        instructor_headers,
    )

    enrolled = client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json={"enrollment_code": course["enrollment_code"]},
    )
    assert enrolled.status_code == 201, enrolled.text

    assessment = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={
            "title": "Week 1 quiz",
            "question_ids": [first_question["id"], second_question["id"]],
        },
    )
    assert assessment.status_code == 201, assessment.text
    assessment_id = assessment.json()["id"]
    published = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text
    safe_detail = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=student_headers,
    )
    assert safe_detail.status_code == 200, safe_detail.text

    attempt = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert attempt.status_code == 201, attempt.text
    attempt_id = attempt.json()["id"]
    first_question_view = next(
        question
        for question in safe_detail.json()["questions"]
        if question["id"] == first_question["id"]
    )
    saved = client.put(
        f"/api/v1/attempts/{attempt_id}/answers/{first_question['id']}",
        headers=student_headers,
        json={"selected_option_id": first_question_view["options"][1]["id"]},
    )
    assert saved.status_code == 200, saved.text
    # The second question is intentionally unanswered and must count as incorrect.
    submitted = client.post(f"/api/v1/attempts/{attempt_id}/submit", headers=student_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["score_percent"] == 50.0

    overview = client.get(
        f"/api/v1/courses/{course_id}/analytics/overview",
        headers=instructor_headers,
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["enrolled_students"] == 1
    assert overview.json()["published_assessments"] == 1
    assert overview.json()["submitted_attempts"] == 1
    assert overview.json()["students_with_submissions"] == 1
    assert overview.json()["average_score_percent"] == 50.0

    topics = client.get(
        f"/api/v1/courses/{course_id}/analytics/topics",
        headers=instructor_headers,
    )
    assert topics.status_code == 200, topics.text
    topic_results = {item["topic_id"]: item for item in topics.json()}
    graph = topic_results[first_topic.json()["id"]]
    combinations = topic_results[second_topic.json()["id"]]
    assert graph["question_presentations"] == 1
    assert graph["correct_responses"] == 1
    assert graph["accuracy_percent"] == 100.0
    assert combinations["question_presentations"] == 1
    assert combinations["correct_responses"] == 0
    assert combinations["accuracy_percent"] == 0.0
    assert combinations["needs_review"] is False

    students = client.get(
        f"/api/v1/courses/{course_id}/analytics/students",
        headers=instructor_headers,
    )
    assert students.status_code == 200, students.text
    assert len(students.json()) == 1
    assert students.json()[0]["submitted_attempts"] == 1
    assert students.json()[0]["average_score_percent"] == 50.0
    assert students.json()[0]["best_score_percent"] == 50.0

    denied = client.get(
        f"/api/v1/courses/{course_id}/analytics/overview",
        headers=student_headers,
    )
    assert denied.status_code == 403


def test_topics_without_submitted_attempts_have_no_accuracy(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "teacher@example.edu", UserRole.INSTRUCTOR)
    course = client.post(
        "/api/v1/courses",
        headers=instructor_headers,
        json={"title": "Algorithms"},
    )
    assert course.status_code == 201, course.text
    topic = client.post(
        f"/api/v1/courses/{course.json()['id']}/topics",
        headers=instructor_headers,
        json={"title": "Sorting"},
    )
    assert topic.status_code == 201, topic.text

    response = client.get(
        f"/api/v1/courses/{course.json()['id']}/analytics/topics",
        headers=instructor_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "topic_id": topic.json()["id"],
            "topic_title": "Sorting",
            "question_presentations": 0,
            "correct_responses": 0,
            "accuracy_percent": None,
            "needs_review": False,
        }
    ]
