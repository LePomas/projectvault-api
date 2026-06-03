from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_documents import router as documents_router
from app.api.routes_projects import project_router, projects_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(documents_router)
router.include_router(projects_router)
router.include_router(project_router)


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "projectvault-api",
    }
