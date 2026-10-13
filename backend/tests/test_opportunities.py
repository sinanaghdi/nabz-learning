from datetime import date, timedelta

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


def opportunity_payload(**overrides):
    data = {
        "title": "پروژهٔ پژوهشی تحلیل داده",
        "category": "research",
        "summary": "همکاری در یک پروژهٔ کاربردی تحلیل داده‌های آموزشی.",
        "description": (
            "برای توسعهٔ یک مطالعهٔ کاربردی به دانشجوی علاقه‌مند نیاز داریم. "
            "همکاری شامل پاک‌سازی داده، تحلیل و ارائهٔ نتایج خواهد بود."
        ),
        "required_skills": "Python، SQL و گزارش‌نویسی",
        "application_url": "https://example.edu/opportunities/123",
        "deadline": (date.today() + timedelta(days=30)).isoformat(),
    }
    data.update(overrides)
    return data


def test_opportunity_submission_review_and_publication(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    student_headers = add_user(test_session, "student@example.edu", UserRole.STUDENT)
    other_student_headers = add_user(test_session, "other@example.edu", UserRole.STUDENT)

    created = client.post("/api/v1/opportunities", headers=student_headers, json=opportunity_payload())
    assert created.status_code == 201, created.text
    submission = created.json()
    opportunity_id = submission["id"]
    assert submission["status"] == "draft"
    assert submission["is_owner"] is True

    # Drafts are visible to the author and moderators, but not other students.
    own_list = client.get("/api/v1/opportunities", headers=student_headers)
    assert own_list.status_code == 200, own_list.text
    assert [item["id"] for item in own_list.json()] == [opportunity_id]
    other_list = client.get("/api/v1/opportunities", headers=other_student_headers)
    assert other_list.status_code == 200, other_list.text
    assert other_list.json() == []
    moderator_list = client.get("/api/v1/opportunities", headers=instructor_headers)
    assert moderator_list.status_code == 200, moderator_list.text
    assert [item["id"] for item in moderator_list.json()] == [opportunity_id]

    forbidden = client.post(
        f"/api/v1/opportunities/{opportunity_id}/publish",
        headers=student_headers,
    )
    assert forbidden.status_code == 403

    published = client.post(
        f"/api/v1/opportunities/{opportunity_id}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    visible = client.get("/api/v1/opportunities?category=research", headers=other_student_headers)
    assert visible.status_code == 200, visible.text
    assert len(visible.json()) == 1
    assert visible.json()[0]["is_owner"] is False
    assert visible.json()[0]["title"] == submission["title"]

    closed = client.post(
        f"/api/v1/opportunities/{opportunity_id}/close",
        headers=student_headers,
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert client.get("/api/v1/opportunities", headers=other_student_headers).json() == []


def test_opportunity_search_and_validation(context) -> None:
    client, test_session = context
    instructor_headers = add_user(test_session, "instructor@example.edu", UserRole.INSTRUCTOR)
    created = client.post(
        "/api/v1/opportunities",
        headers=instructor_headers,
        json=opportunity_payload(category="internship", title="کارآموزی مهندسی نرم‌افزار"),
    )
    assert created.status_code == 201, created.text

    invalid_url = client.post(
        "/api/v1/opportunities",
        headers=instructor_headers,
        json=opportunity_payload(application_url="javascript:alert(1)"),
    )
    assert invalid_url.status_code == 422

    invalid_category = client.post(
        "/api/v1/opportunities",
        headers=instructor_headers,
        json=opportunity_payload(category="promotion"),
    )
    assert invalid_category.status_code == 422

    published = client.post(
        f"/api/v1/opportunities/{created.json()['id']}/publish",
        headers=instructor_headers,
    )
    assert published.status_code == 200, published.text
    search = client.get(
        "/api/v1/opportunities?q=مهندسی&category=internship",
        headers=instructor_headers,
    )
    assert search.status_code == 200, search.text
    assert len(search.json()) == 1
    assert search.json()[0]["category"] == "internship"


def test_opportunity_routes_require_authentication(context) -> None:
    client, _ = context
    response = client.get("/api/v1/opportunities")
    assert response.status_code == 401
    response = client.post("/api/v1/opportunities", json=opportunity_payload())
    assert response.status_code == 401
