from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.opportunities import Opportunity, OpportunityCategory, OpportunityStatus
from app.models.user import User, UserRole
from app.schemas.opportunities import OpportunityCreate, OpportunityRead

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def opportunity_read(item: Opportunity, current_user: User) -> OpportunityRead:
    return OpportunityRead(
        id=item.id,
        posted_by_id=item.posted_by_id,
        category=OpportunityCategory(item.category),
        title=item.title,
        summary=item.summary,
        description=item.description,
        required_skills=item.required_skills,
        application_url=item.application_url,
        deadline=item.deadline,
        status=OpportunityStatus(item.status),
        created_at=item.created_at,
        updated_at=item.updated_at,
        published_at=item.published_at,
        is_owner=item.posted_by_id == current_user.id,
    )


def get_opportunity_or_404(db: Session, opportunity_id: int) -> Opportunity:
    item = db.get(Opportunity, opportunity_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return item


def can_moderate(user: User) -> bool:
    return user.role in {UserRole.INSTRUCTOR.value, UserRole.ADMIN.value}


@router.get(
    "",
    response_model=list[OpportunityRead],
    summary="List published opportunities and submissions visible to the current user",
)
def list_opportunities(
    category: OpportunityCategory | None = None,
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OpportunityRead]:
    statement = select(Opportunity)
    if not can_moderate(current_user):
        statement = statement.where(
            or_(
                Opportunity.status == OpportunityStatus.PUBLISHED.value,
                Opportunity.posted_by_id == current_user.id,
            )
        )
    if category is not None:
        statement = statement.where(Opportunity.category == category.value)
    if q is not None:
        term = "%" + q.strip() + "%"
        statement = statement.where(
            or_(
                Opportunity.title.ilike(term),
                Opportunity.summary.ilike(term),
                Opportunity.description.ilike(term),
                Opportunity.required_skills.ilike(term),
            )
        )
    items = db.scalars(
        statement.order_by(Opportunity.updated_at.desc(), Opportunity.id.desc()).limit(limit)
    ).all()
    return [opportunity_read(item, current_user) for item in items]


@router.post(
    "",
    response_model=OpportunityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an opportunity for review",
)
def create_opportunity(
    payload: OpportunityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OpportunityRead:
    item = Opportunity(
        posted_by_id=current_user.id,
        title=" ".join(payload.title.split()),
        category=payload.category.value,
        summary=" ".join(payload.summary.split()),
        description=payload.description.strip(),
        required_skills=payload.required_skills,
        application_url=payload.application_url,
        deadline=payload.deadline,
        status=OpportunityStatus.DRAFT.value,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return opportunity_read(item, current_user)


@router.post(
    "/{opportunity_id}/publish",
    response_model=OpportunityRead,
    summary="Publish an opportunity after review",
)
def publish_opportunity(
    opportunity_id: int,
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> OpportunityRead:
    item = get_opportunity_or_404(db, opportunity_id)
    if item.status != OpportunityStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only draft opportunities can be published.")
    item.status = OpportunityStatus.PUBLISHED.value
    item.published_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return opportunity_read(item, current_user)


@router.post(
    "/{opportunity_id}/close",
    response_model=OpportunityRead,
    summary="Close an opportunity",
)
def close_opportunity(
    opportunity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OpportunityRead:
    item = get_opportunity_or_404(db, opportunity_id)
    if item.posted_by_id != current_user.id and not can_moderate(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only the author or a moderator can close this opportunity.",
        )
    if item.status == OpportunityStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="This opportunity is already closed.")
    item.status = OpportunityStatus.CLOSED.value
    db.commit()
    db.refresh(item)
    return opportunity_read(item, current_user)
