from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_exception_handler(AppError, app_error_handler)
app.include_router(router)
