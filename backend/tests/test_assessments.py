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


def setup_course_and_question(
    client: TestClient, instructor_headers: dict[str, str]
) -> tuple[int, int]:
    course_response = client.post(
        "/api/v1/courses",
        headers=instructor_headers,
        json={"title": "Computer Networks"},
    )
    assert course_response.status_code == 201, course_response.text
    course_id = course_response.json()["id"]
    topic_response = client.post(
        f"/api/v1/courses/{course_id}/topics",
        headers=instructor_headers,
        json={"title": "Routing"},
    )
    assert topic_response.status_code == 201, topic_response.text
    question_response = client.post(
        f"/api/v1/courses/{course_id}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic_response.json()["id"],
            "prompt": "Which layer routes IP packets?",
            "status": "published",
            "options": [
                {"text": "Application", "is_correct": False},
                {"text": "Network", "is_correct": True},
            ],
        },
    )
    assert question_response.status_code == 201, question_response.text
    return course_id, question_response.json()["id"]


def test_student_attempt_hides_answer_key_and_is_scored(context) -> None:
    client, test_session = context
    instructor_headers = add_user(
        test_session, "instructor@example.edu", UserRole.INSTRUCTOR
    )
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course_id, question_id = setup_course_and_question(client, instructor_headers)

    instructor_course = client.get(f"/api/v1/courses/{course_id}", headers=instructor_headers)
    assert instructor_course.status_code == 200
    enrollment_code = client.get(
        f"/api/v1/courses/{course_id}", headers=instructor_headers
    ).json()
    assert "enrollment_code" not in enrollment_code

    # The test can read the join code from the course-created response; recreate course lookup
    # through a second course create response is intentionally avoided, so query the database.
    with test_session() as db:
        from app.models.course import Course

        code = db.get(Course, course_id).enrollment_code
    enrolled = client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json={"enrollment_code": code},
    )
    assert enrolled.status_code == 201, enrolled.text

    draft = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={
            "title": "Routing quiz",
            "question_ids": [question_id],
            "duration_minutes": 10,
            "max_attempts": 1,
        },
    )
    assert draft.status_code == 201, draft.text
    assessment_id = draft.json()["id"]
    published = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text

    detail = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=student_headers,
    )
    assert detail.status_code == 200, detail.text
    assert "is_correct" not in detail.text
    assert "explanation" not in detail.text

    attempt_response = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert attempt_response.status_code == 201, attempt_response.text
    attempt_id = attempt_response.json()["id"]

    saved = client.put(
        f"/api/v1/attempts/{attempt_id}/answers/{question_id}",
        headers=student_headers,
        json={"selected_option_id": detail.json()["questions"][0]["options"][1]["id"]},
    )
    assert saved.status_code == 200, saved.text
    assert len(saved.json()["answers"]) == 1

    submitted = client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers=student_headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["correct_count"] == 1
    assert submitted.json()["score_percent"] == 100.0

    repeated = client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers=student_headers,
    )
    assert repeated.status_code == 409

    no_more_attempts = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert no_more_attempts.status_code == 409


def test_students_cannot_view_draft_assessment_or_start_it(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course_id, question_id = setup_course_and_question(client, instructor_headers)
    with test_session() as db:
        from app.models.course import Course

        code = db.get(Course, course_id).enrollment_code
    assert client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json={"enrollment_code": code},
    ).status_code == 201
    draft = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={"title": "Draft quiz", "question_ids": [question_id]},
    )
    assert draft.status_code == 201
    assessment_id = draft.json()["id"]
    assert client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=student_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    ).status_code == 409


def test_assessment_rejects_question_from_another_course(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    course_id, _ = setup_course_and_question(client, instructor_headers)
    second_course_response = client.post(
        "/api/v1/courses", headers=instructor_headers, json={"title": "Another course"}
    )
    second_course_id = second_course_response.json()["id"]
    response = client.post(
        f"/api/v1/courses/{second_course_id}/assessments",
        headers=instructor_headers,
        json={"title": "Invalid assessment", "question_ids": [1]},
    )
    assert response.status_code == 422



def test_draft_assessment_can_replace_its_question_list(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    course_id, first_question_id = setup_course_and_question(client, instructor_headers)
    topic_response = client.post(
        f"/api/v1/courses/{course_id}/topics",
        headers=instructor_headers,
        json={"title": "IP addressing"},
    )
    assert topic_response.status_code == 201, topic_response.text
    second_question = client.post(
        f"/api/v1/courses/{course_id}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic_response.json()["id"],
            "prompt": "Which protocol assigns IP addresses dynamically?",
            "status": "published",
            "options": [
                {"text": "DHCP", "is_correct": True},
                {"text": "FTP", "is_correct": False},
            ],
        },
    )
    assert second_question.status_code == 201, second_question.text
    second_question_id = second_question.json()["id"]

    created = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={"title": "Editable draft", "question_ids": [first_question_id]},
    )
    assert created.status_code == 201, created.text
    assessment_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=instructor_headers,
        json={"question_ids": [second_question_id]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["question_count"] == 1

    detail = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=instructor_headers,
    )
    assert detail.status_code == 200, detail.text
    assert [item["id"] for item in detail.json()["questions"]] == [second_question_id]



def test_active_attempt_can_be_resumed_without_consuming_another_attempt(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course_id, question_id = setup_course_and_question(client, instructor_headers)

    with test_session() as db:
        from app.models.course import Course

        code = db.get(Course, course_id).enrollment_code
    enrolled = client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json={"enrollment_code": code},
    )
    assert enrolled.status_code == 201, enrolled.text

    created = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={
            "title": "Resumable quiz",
            "question_ids": [question_id],
            "max_attempts": 1,
        },
    )
    assert created.status_code == 201, created.text
    assessment_id = created.json()["id"]
    published = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text

    detail = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=student_headers,
    )
    option_id = detail.json()["questions"][0]["options"][0]["id"]
    started = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert started.status_code == 201, started.text
    attempt_id = started.json()["id"]

    saved = client.put(
        f"/api/v1/attempts/{attempt_id}/answers/{question_id}",
        headers=student_headers,
        json={"selected_option_id": option_id},
    )
    assert saved.status_code == 200, saved.text

    resumed = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts/active",
        headers=student_headers,
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["id"] == attempt_id
    assert resumed.json()["status"] == "in_progress"
    assert resumed.json()["answers"] == [
        {"question_id": question_id, "selected_option_id": option_id}
    ]

    repeated_start = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert repeated_start.status_code == 200, repeated_start.text
    assert repeated_start.json()["id"] == attempt_id


def test_active_attempt_endpoint_is_scoped_to_the_current_student(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    other_student_headers = add_user(
        test_session, "other-student@example.edu", UserRole.STUDENT
    )
    course_id, question_id = setup_course_and_question(client, instructor_headers)

    with test_session() as db:
        from app.models.course import Course

        code = db.get(Course, course_id).enrollment_code
    for headers in (student_headers, other_student_headers):
        enrolled = client.post(
            "/api/v1/courses/enroll",
            headers=headers,
            json={"enrollment_code": code},
        )
        assert enrolled.status_code == 201, enrolled.text

    created = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={"title": "Private attempt", "question_ids": [question_id]},
    )
    assert created.status_code == 201, created.text
    assessment_id = created.json()["id"]
    published = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text

    started = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert started.status_code == 201, started.text

    hidden_from_other_student = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts/active",
        headers=other_student_headers,
    )
    assert hidden_from_other_student.status_code == 200
    assert hidden_from_other_student.json() is None

    cannot_read_other_attempt = client.get(
        f"/api/v1/attempts/{started.json()['id']}",
        headers=other_student_headers,
    )
    assert cannot_read_other_attempt.status_code == 403


def test_answer_rejects_option_from_another_question(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    course_id, first_question_id = setup_course_and_question(client, instructor_headers)

    topic = client.get(
        f"/api/v1/courses/{course_id}/topics",
        headers=instructor_headers,
    )
    assert topic.status_code == 200, topic.text
    topic_id = topic.json()[0]["id"]
    second_question = client.post(
        f"/api/v1/courses/{course_id}/questions",
        headers=instructor_headers,
        json={
            "topic_id": topic_id,
            "prompt": "Which protocol resolves an IP address to a MAC address?",
            "status": "published",
            "options": [
                {"text": "ARP", "is_correct": True},
                {"text": "DNS", "is_correct": False},
            ],
        },
    )
    assert second_question.status_code == 201, second_question.text

    with test_session() as db:
        from app.models.course import Course

        code = db.get(Course, course_id).enrollment_code
    enrolled = client.post(
        "/api/v1/courses/enroll",
        headers=student_headers,
        json={"enrollment_code": code},
    )
    assert enrolled.status_code == 201, enrolled.text

    created = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={"title": "Option ownership", "question_ids": [first_question_id]},
    )
    assert created.status_code == 201, created.text
    assessment_id = created.json()["id"]
    published = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text
    started = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
        headers=student_headers,
    )
    assert started.status_code == 201, started.text

    invalid_answer = client.put(
        f"/api/v1/attempts/{started.json()['id']}/answers/{first_question_id}",
        headers=student_headers,
        json={"selected_option_id": second_question.json()["options"][0]["id"]},
    )
    assert invalid_answer.status_code == 422



def test_course_leaderboard_ranks_results_and_masks_peer_names(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    top_student_headers = add_user(test_session, "top@example.edu", UserRole.STUDENT)
    peer_headers = add_user(test_session, "peer@example.edu", UserRole.STUDENT)
    outsider_headers = add_user(test_session, "outsider@example.edu", UserRole.STUDENT)
    course_id, question_id = setup_course_and_question(client, instructor_headers)

    with test_session() as db:
        from app.models.course import Course

        enrollment_code = db.get(Course, course_id).enrollment_code

    for headers in (top_student_headers, peer_headers):
        enrolled = client.post(
            "/api/v1/courses/enroll",
            headers=headers,
            json={"enrollment_code": enrollment_code},
        )
        assert enrolled.status_code == 201, enrolled.text

    draft = client.post(
        f"/api/v1/courses/{course_id}/assessments",
        headers=instructor_headers,
        json={"title": "Leaderboard test", "question_ids": [question_id]},
    )
    assert draft.status_code == 201, draft.text
    assessment_id = draft.json()["id"]
    published = client.post(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text
    detail = client.get(
        f"/api/v1/courses/{course_id}/assessments/{assessment_id}",
        headers=top_student_headers,
    )
    assert detail.status_code == 200, detail.text
    options = detail.json()["questions"][0]["options"]

    for headers, selected_index in ((top_student_headers, 1), (peer_headers, 0)):
        attempt = client.post(
            f"/api/v1/courses/{course_id}/assessments/{assessment_id}/attempts",
            headers=headers,
        )
        assert attempt.status_code == 201, attempt.text
        attempt_id = attempt.json()["id"]
        saved = client.put(
            f"/api/v1/attempts/{attempt_id}/answers/{question_id}",
            headers=headers,
            json={"selected_option_id": options[selected_index]["id"]},
        )
        assert saved.status_code == 200, saved.text
        submitted = client.post(
            f"/api/v1/attempts/{attempt_id}/submit",
            headers=headers,
        )
        assert submitted.status_code == 200, submitted.text

    student_view = client.get(
        f"/api/v1/courses/{course_id}/leaderboard",
        headers=top_student_headers,
    )
    assert student_view.status_code == 200, student_view.text
    student_rows = student_view.json()
    assert student_rows[0]["rank"] == 1
    assert student_rows[0]["display_name"] == "شما"
    assert student_rows[0]["is_current_user"] is True
    assert student_rows[0]["average_score_percent"] == 100.0
    assert student_rows[1]["rank"] == 2
    assert student_rows[1]["display_name"] == "دانشجوی رتبهٔ ۲"
    assert "Peer" not in student_view.text
    assert "Top" not in student_view.text

    instructor_view = client.get(
        f"/api/v1/courses/{course_id}/leaderboard",
        headers=instructor_headers,
    )
    assert instructor_view.status_code == 200, instructor_view.text
    assert {entry["display_name"] for entry in instructor_view.json()} == {"Top", "Peer"}

    denied = client.get(
        f"/api/v1/courses/{course_id}/leaderboard",
        headers=outsider_headers,
    )
    assert denied.status_code == 403
