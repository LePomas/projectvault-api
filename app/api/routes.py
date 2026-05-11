from fastapi import APIRouter

from app.api.routes_auth import router as auth_router

router = APIRouter()
router.include_router(auth_router)


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "projectvault-api",
    }
