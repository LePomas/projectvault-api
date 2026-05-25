from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session
from starlette.types import Receive, Scope, Send

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentCompleteUploadRequest,
    DocumentDownloadUrlRead,
    DocumentPresignUploadRead,
    DocumentPresignUploadRequest,
    DocumentRead,
    DocumentUpdate,
)
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


def _attachment_header(filename: str) -> str:
    quoted = quote(filename)
    if quoted != filename:
        return f"attachment; filename*=utf-8''{quoted}"
    escaped = filename.replace("\\", "\\\\").replace('"', '\\"')
    return f'attachment; filename="{escaped}"'


class LocalFileResponse(Response):
    def __init__(self, path: Path, media_type: str, filename: str) -> None:
        self.path = path
        super().__init__(
            content=None,
            media_type=media_type,
            headers={"Content-Disposition": _attachment_header(filename)},
        )
        if "content-length" in self.headers:
            del self.headers["content-length"]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        with self.path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    }
                )
        await send({"type": "http.response.body", "body": b"", "more_body": False})


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> Document:
    return DocumentService(db).upload(project_id, file, current_user)


@router.post(
    "/projects/{project_id}/documents/presign-upload",
    response_model=DocumentPresignUploadRead,
    status_code=status.HTTP_201_CREATED,
)
async def presign_document_upload(
    project_id: int,
    payload: DocumentPresignUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentPresignUploadRead:
    return DocumentService(db).presign_upload(project_id, payload, current_user)


@router.post(
    "/projects/{project_id}/documents/complete-upload",
    response_model=DocumentRead,
)
async def complete_document_upload(
    project_id: int,
    payload: DocumentCompleteUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    return DocumentService(db).complete_upload(project_id, payload, current_user)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_project_documents(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Document]:
    return DocumentService(db).list_for_project(project_id, current_user)


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    return DocumentService(db).get(document_id, current_user)


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    download = DocumentService(db).download(document_id, current_user)
    return LocalFileResponse(
        path=download.path,
        media_type=download.document.content_type,
        filename=download.document.filename,
    )


@router.get(
    "/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlRead,
)
async def get_document_download_url(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentDownloadUrlRead:
    download = DocumentService(db).download_url(document_id, current_user)
    return DocumentDownloadUrlRead(
        download_url=download.url,
        expires_in=download.expires_in,
    )


@router.patch("/documents/{document_id}", response_model=DocumentRead)
@router.put("/documents/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    payload: DocumentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    return DocumentService(db).update(document_id, payload, current_user)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    DocumentService(db).delete(document_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
