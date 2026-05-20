from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentUpdate
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


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
