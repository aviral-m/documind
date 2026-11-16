import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import VerifiedUser
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal, get_db
from app.schemas.documents import DocumentResponse
from app.services import document_service
from app.services.document_service import DocumentNotFound, UploadRejected
from app.services.storage import CloudinaryStorage, FileStorage, StorageError

router = APIRouter(prefix="/documents", tags=["documents"])
DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_session_factory() -> sessionmaker[Session]:
    return SessionLocal


SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def get_file_storage(settings: SettingsDep) -> FileStorage:
    try:
        return CloudinaryStorage(settings.cloudinary_url)
    except StorageError as exc:
        raise HTTPException(status_code=500, detail="Document storage isn't configured.") from exc


StorageDep = Annotated[FileStorage, Depends(get_file_storage)]


@router.post("", status_code=202, response_model=DocumentResponse)
def upload_document(
    user: VerifiedUser,
    file: Annotated[UploadFile, File()],
    background_tasks: BackgroundTasks,
    db: DbSession,
    settings: SettingsDep,
    storage: StorageDep,
    session_factory: SessionFactoryDep,
) -> DocumentResponse:
    try:
        document = document_service.store_upload(db, settings, storage, user, file)
    except UploadRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except StorageError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    background_tasks.add_task(
        document_service.process_document, session_factory, settings, storage, document.id
    )
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(user: VerifiedUser, db: DbSession) -> list[DocumentResponse]:
    documents = document_service.list_documents(db, user)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, user: VerifiedUser, db: DbSession) -> DocumentResponse:
    try:
        document = document_service.get_user_document(db, user, document_id)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    user: VerifiedUser,
    db: DbSession,
    storage: StorageDep,
) -> Response:
    try:
        document_service.delete_document(db, storage, user, document_id)
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    return Response(status_code=204)
