from pathlib import Path, PurePosixPath
from shutil import copyfileobj
from typing import BinaryIO
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import AppError


class LocalDocumentStorage:
    def __init__(self, root_path: str | Path | None = None) -> None:
        self.root_path = Path(root_path or settings.document_storage_path)

    def generate_key(self, project_id: int, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return str(PurePosixPath("projects", str(project_id), f"{uuid4().hex}{suffix}"))

    def save(self, storage_key: str, source: BinaryIO) -> int:
        path = self._path_for_key(storage_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as destination:
                copyfileobj(source, destination)
        except OSError as exc:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be stored.",
            ) from exc
        return path.stat().st_size

    def delete(self, storage_key: str) -> None:
        path = self._path_for_key(storage_key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be deleted from storage.",
            ) from exc

    def _path_for_key(self, storage_key: str) -> Path:
        key_path = PurePosixPath(storage_key)
        if key_path.is_absolute() or ".." in key_path.parts:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document storage key is invalid.",
            )
        return self.root_path.joinpath(*key_path.parts)
