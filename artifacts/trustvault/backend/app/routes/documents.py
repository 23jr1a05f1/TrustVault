
"""Private document upload, download, restore, and version-history endpoints."""

from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.authorization import can_read, effective_document_role, record_audit
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, DocumentVersion, User
from app.storage import (
    STORAGE_BACKEND,
    copy_object,
    delete_object,
    new_storage_key as generate_storage_key,
    object_exists,
    read_bytes,
    save_bytes,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MiB
CHUNK_SIZE = 64 * 1024
STORAGE_DIR = Path(
    __import__("os").environ.get("TRUSTVAULT_STORAGE_DIR", "private_storage")
).resolve()


def _audit(
    db: Session,
    user: User,
    event_type: str,
    outcome: str,
    document_id: str,
    details: dict | None = None,
) -> None:
    record_audit(
        db,
        actor=user,
        event_type=event_type,
        outcome=outcome,
        resource_type="document",
        resource_id=document_id,
        details=details or {},
    )


def _get_document_role(
    db: Session,
    user: User,
    document_id: UUID,
) -> tuple[Document, str]:
    """Load a document and enforce its current server-side access role."""
    document = db.get(Document, document_id)
    role = (
        effective_document_role(db, user, document)
        if document is not None
        else None
    )

    if document is None or role is None or not can_read(role):
        _audit(
            db,
            user,
            "document.download.denied",
            "denied",
            str(document_id),
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document not found")

    return document, role


def _safe_file_path(storage_key: str) -> Path | None:
    """Return a safe local path if the requested file exists."""
    if not storage_key or Path(storage_key).name != storage_key:
        return None

    file_path = (STORAGE_DIR / storage_key).resolve()

    if file_path.parent != STORAGE_DIR or not file_path.is_file():
        return None

    return file_path


def _storage_file_exists(storage_key: str) -> bool:
    """Check for an object in the explicitly selected storage backend."""
    try:
        return object_exists(storage_key)
    except (ValueError, RuntimeError):
        return False


def _cleanup_storage_key(storage_key: str | None) -> None:
    """Best-effort cleanup after a failed database operation."""
    if storage_key is None:
        return

    try:
        delete_object(storage_key)
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Could not clean up stored object after a failed operation"
        )


def _download_response(
    storage_key: str,
    filename: str,
    content_type: str | None,
) -> Response:
    """Return a private download response for either storage backend."""
    if not storage_key or Path(storage_key).name != storage_key:
        raise HTTPException(status_code=404, detail="Document file not found")

    media_type = content_type or "application/octet-stream"

    if STORAGE_BACKEND == "local":
        file_path = _safe_file_path(storage_key)
        if file_path is None:
            raise HTTPException(
                status_code=404,
                detail="Document file not found",
            )

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    content = read_bytes(storage_key)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(filename, safe='')}"
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _save_upload(file: UploadFile) -> tuple[str, int]:
    """Save an upload under a server-generated key and enforce the size limit."""
    storage_key = generate_storage_key()
    chunks: list[bytes] = []
    size = 0

    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break

            size += len(chunk)
            if size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="File exceeds the 10 MiB upload limit",
                )

            chunks.append(chunk)

        save_bytes(storage_key, b"".join(chunks))
        return storage_key, size

    except Exception:
        _cleanup_storage_key(storage_key)
        raise


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general", max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a document and its initial version."""
    original_name = (file.filename or "document").replace("\\", "/").split("/")[-1]
    original_name = original_name[:255].strip()

    if not original_name:
        await file.close()
        raise HTTPException(status_code=400, detail="A filename is required")

    storage_key: str | None = None

    try:
        storage_key, size = await _save_upload(file)
        content_type = file.content_type or "application/octet-stream"

        document = Document(
            owner_id=user.id,
            name=original_name,
            category=category.strip() or "general",
            content_type=content_type,
            size_bytes=size,
            storage_key=storage_key,
        )
        db.add(document)
        db.flush()

        db.add(
            DocumentVersion(
                document_id=document.id,
                version_number=1,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size,
                uploaded_by_id=user.id,
            )
        )

        _audit(
            db,
            user,
            "document.uploaded",
            "success",
            str(document.id),
            {"size_bytes": size, "version_number": 1},
        )
        db.commit()
        db.refresh(document)

        return {
            "id": str(document.id),
            "name": document.name,
            "category": document.category,
            "size_bytes": document.size_bytes,
            "version_number": 1,
        }

    except Exception:
        db.rollback()
        _cleanup_storage_key(storage_key)
        raise

    finally:
        await file.close()


@router.post(
    "/{document_id}/versions",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_version(
    document_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a new version. Only document Owners and Editors may do this."""
    document, role = _get_document_role(db, user, document_id)

    if role not in ("admin", "owner", "editor"):
        _audit(
            db,
            user,
            "document.version.upload.denied",
            "denied",
            str(document_id),
        )
        db.commit()
        await file.close()
        raise HTTPException(status_code=404, detail="Document not found")

    storage_key: str | None = None

    try:
        storage_key, size = await _save_upload(file)
        content_type = file.content_type or "application/octet-stream"

        current_max = db.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document.id
            )
        )
        next_version = (current_max or 0) + 1

        version = DocumentVersion(
            document_id=document.id,
            version_number=next_version,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=size,
            uploaded_by_id=user.id,
        )
        db.add(version)

        document.storage_key = storage_key
        document.content_type = content_type
        document.size_bytes = size

        _audit(
            db,
            user,
            "document.version.uploaded",
            "success",
            str(document.id),
            {"version_number": next_version, "size_bytes": size},
        )

        db.commit()
        db.refresh(version)

        return {
            "document_id": str(document.id),
            "version_number": next_version,
            "size_bytes": size,
            "created_at": version.created_at,
        }

    except Exception:
        db.rollback()
        _cleanup_storage_key(storage_key)
        raise

    finally:
        await file.close()


@router.get("/{document_id}/versions")
def list_document_versions(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List version metadata for Owners and Editors; only Owners see uploader identity."""
    document, role = _get_document_role(db, user, document_id)

    if role not in ("admin", "owner", "editor"):
        _audit(
            db,
            user,
            "document.version.history.denied",
            "denied",
            str(document_id),
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document not found")

    versions = db.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())
    ).all()

    result: list[dict] = []

    for version in versions:
        entry = {
            "version_number": version.version_number,
            "size_bytes": version.size_bytes,
            "content_type": version.content_type,
            "created_at": version.created_at,
        }

        if role in ("admin", "owner"):
            uploader = (
                db.get(User, version.uploaded_by_id)
                if version.uploaded_by_id is not None
                else None
            )
            entry["uploaded_by"] = (
                {"id": str(uploader.id), "email": uploader.email}
                if uploader is not None
                else None
            )

        result.append(entry)

    _audit(
        db,
        user,
        "document.version.history.viewed",
        "success",
        str(document.id),
        {"returned_count": len(result)},
    )
    db.commit()

    return result


@router.post("/{document_id}/versions/{version_number}/restore")
def restore_document_version(
    document_id: UUID,
    version_number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Restore an old version as a new version. Only Owners and Admins may restore."""
    document, role = _get_document_role(db, user, document_id)

    if role not in ("admin", "owner"):
        _audit(
            db,
            user,
            "document.version.restore.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document not found")

    if version_number < 1:
        _audit(
            db,
            user,
            "document.version.restore.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document version not found")

    source_version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_number == version_number,
        )
    )

    if source_version is None:
        _audit(
            db,
            user,
            "document.version.restore.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document version not found")

    if not _storage_file_exists(source_version.storage_key):
        _audit(
            db,
            user,
            "document.version.restore.denied",
            "denied",
            str(document_id),
            {
                "version_number": version_number,
                "reason": "source_file_missing",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=404,
            detail="Document version file not found",
        )

    current_max = db.scalar(
        select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == document.id
        )
    )
    next_version = (current_max or 0) + 1

    restored_storage_key = generate_storage_key()

    try:
        copy_object(source_version.storage_key, restored_storage_key)

        restored_version = DocumentVersion(
            document_id=document.id,
            version_number=next_version,
            storage_key=restored_storage_key,
            content_type=source_version.content_type,
            size_bytes=source_version.size_bytes,
            uploaded_by_id=user.id,
        )
        db.add(restored_version)

        document.storage_key = restored_storage_key
        document.content_type = source_version.content_type
        document.size_bytes = source_version.size_bytes

        _audit(
            db,
            user,
            "document.version.restored",
            "success",
            str(document.id),
            {
                "restored_from_version": version_number,
                "new_version_number": next_version,
                "size_bytes": source_version.size_bytes,
            },
        )

        db.commit()
        db.refresh(restored_version)

        return {
            "document_id": str(document.id),
            "restored_from_version": version_number,
            "version_number": restored_version.version_number,
            "size_bytes": restored_version.size_bytes,
            "created_at": restored_version.created_at,
        }

    except Exception:
        db.rollback()
        _cleanup_storage_key(restored_storage_key)
        raise


@router.get("/{document_id}/versions/{version_number}/download")
def download_document_version(
    document_id: UUID,
    version_number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download a previous version. Owners and Editors may access version history."""
    document, role = _get_document_role(db, user, document_id)

    if role not in ("admin", "owner", "editor"):
        _audit(
            db,
            user,
            "document.version.download.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document version not found")

    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_number == version_number,
        )
    )

    if version is None:
        _audit(
            db,
            user,
            "document.version.download.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document version not found")

    if not _storage_file_exists(version.storage_key):
        _audit(
            db,
            user,
            "document.version.download.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(
            status_code=404,
            detail="Document version file not found",
        )

    _audit(
        db,
        user,
        "document.version.downloaded",
        "success",
        str(document.id),
        {"version_number": version_number},
    )
    db.commit()

    return _download_response(
        version.storage_key,
        document.name,
        version.content_type,
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download the latest document when the user has read access."""
    document, role = _get_document_role(db, user, document_id)

    if not _storage_file_exists(document.storage_key):
        _audit(
            db,
            user,
            "document.download.denied",
            "denied",
            str(document_id),
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document file not found")

    _audit(
        db,
        user,
        "document.downloaded",
        "success",
        str(document.id),
    )
    db.commit()

    return _download_response(
        document.storage_key,
        document.name,
        document.content_type,
    )
