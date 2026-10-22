
"""Private document upload, download, and version-history endpoints."""

import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.authorization import can_read, effective_document_role, record_audit
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, DocumentVersion, User

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MiB
CHUNK_SIZE = 64 * 1024
STORAGE_DIR = Path(
    os.environ.get("TRUSTVAULT_STORAGE_DIR", "private_storage")
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
    """Return a path inside private storage, or None for an invalid/missing file."""
    if not storage_key or Path(storage_key).name != storage_key:
        return None

    file_path = (STORAGE_DIR / storage_key).resolve()

    if file_path.parent != STORAGE_DIR or not file_path.is_file():
        return None

    return file_path


async def _save_upload(file: UploadFile) -> tuple[str, int]:
    """Save an upload under a server-generated key and enforce the size limit."""
    storage_key = uuid4().hex
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    destination = STORAGE_DIR / storage_key
    size = 0

    try:
        with destination.open("xb") as output:
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

                output.write(chunk)

        return storage_key, size

    except Exception:
        destination.unlink(missing_ok=True)
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
        if storage_key is not None:
            (STORAGE_DIR / storage_key).unlink(missing_ok=True)
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
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

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

        # Point the document at the latest file while preserving older versions.
        document.storage_key = storage_key
        document.content_type = content_type
        document.size_bytes = size

        _audit(
            db,
            user,
            "document.version.uploaded",
            "success",
            str(document.id),
            {
                "version_number": next_version,
                "size_bytes": size,
            },
        )

        db.commit()

        return {
            "document_id": str(document.id),
            "version_number": next_version,
            "size_bytes": size,
            "created_at": version.created_at,
        }

    except Exception:
        db.rollback()
        if storage_key is not None:
            (STORAGE_DIR / storage_key).unlink(missing_ok=True)
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
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

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


@router.get("/{document_id}/versions/{version_number}/download")
def download_document_version(
    document_id: UUID,
    version_number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
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

    file_path = _safe_file_path(version.storage_key)

    if file_path is None:
        _audit(
            db,
            user,
            "document.version.download.denied",
            "denied",
            str(document_id),
            {"version_number": version_number},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Document version file not found")

    _audit(
        db,
        user,
        "document.version.downloaded",
        "success",
        str(document.id),
        {"version_number": version_number},
    )
    db.commit()

    return FileResponse(
        path=file_path,
        media_type=version.content_type,
        filename=document.name,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download the latest document when the user has read access."""
    document, role = _get_document_role(db, user, document_id)

    file_path = _safe_file_path(document.storage_key)

    if file_path is None:
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

    return FileResponse(
        path=file_path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.name,
        headers={"Cache-Control": "private, no-store"},
    )
