from fastapi import APIRouter

from app.api.auth import router as auth_router

api_router = APIRouter()


@api_router.get("/health", tags=["health"], summary="Check API health")
def health_check() -> dict[str, str]:
    """Lightweight process health endpoint; it does not assert database readiness."""
    return {"status": "ok", "service": "nabz-learning-api"}


api_router.include_router(auth_router)
