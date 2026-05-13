from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_projects import router as projects_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(projects_router)


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "projectvault-api",
    }
