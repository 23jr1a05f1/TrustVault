
"""Local and S3-compatible private document storage."""

import os
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

STORAGE_DIR = Path(
    os.environ.get("TRUSTVAULT_STORAGE_DIR", "private_storage")
).resolve()

STORAGE_BACKEND = os.environ.get(
    "TRUSTVAULT_STORAGE_BACKEND", "local"
).strip().lower()

MAX_FILE_SIZE = 10 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


def _local_storage_dir() -> Path:
    """Return the active local directory, respecting document-route test overrides."""
    # Import lazily to avoid a circular import during application startup.
    try:
        from app.routes import documents

        if STORAGE_BACKEND == "local":
            route_dir = getattr(documents, "STORAGE_DIR", None)
            if route_dir is not None:
                return Path(route_dir).resolve()
    except (ImportError, AttributeError):
        pass

    return STORAGE_DIR


def _validate_key(storage_key: str) -> str:
    """Accept only the simple server-generated storage keys used by TrustVault."""
    if not storage_key or Path(storage_key).name != storage_key:
        raise ValueError("Invalid storage key")
    return storage_key


def _s3_client():
    """Build an S3-compatible client only when S3 storage is enabled."""
    endpoint_url = os.environ.get("NEON_S3_ENDPOINT_URL")
    access_key = os.environ.get("NEON_S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("NEON_S3_SECRET_ACCESS_KEY")
    region = os.environ.get("NEON_S3_REGION", "us-east-1")

    if not all((endpoint_url, access_key, secret_key)):
        raise RuntimeError(
            "S3 storage is enabled but its endpoint or credentials are missing"
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


def _bucket_name() -> str:
    bucket = os.environ.get("NEON_S3_BUCKET", "trustvault-documents").strip()
    if not bucket:
        raise RuntimeError("NEON_S3_BUCKET must not be empty")
    return bucket


def object_exists(storage_key: str) -> bool:
    """Return whether a private object exists in the selected storage backend."""
    key = _validate_key(storage_key)

    if STORAGE_BACKEND == "local":
        directory = _local_storage_dir()
        path = (directory / key).resolve()
        return path.parent == directory and path.is_file()

    if STORAGE_BACKEND != "s3":
        raise RuntimeError("TRUSTVAULT_STORAGE_BACKEND must be 'local' or 's3'")

    try:
        _s3_client().head_object(Bucket=_bucket_name(), Key=key)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status_code = exc.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if code in ("404", "NoSuchKey", "NotFound") or status_code == 404:
            return False
        raise


def save_bytes(storage_key: str, content: bytes) -> None:
    """Save content under an existing server-generated key."""
    key = _validate_key(storage_key)

    if STORAGE_BACKEND == "local":
        directory = _local_storage_dir()
        directory.mkdir(parents=True, exist_ok=True)
        destination = (directory / key).resolve()

        if destination.parent != directory:
            raise ValueError("Invalid storage key")

        with destination.open("xb") as output:
            output.write(content)
        return

    if STORAGE_BACKEND != "s3":
        raise RuntimeError("TRUSTVAULT_STORAGE_BACKEND must be 'local' or 's3'")

    _s3_client().put_object(
        Bucket=_bucket_name(),
        Key=key,
        Body=content,
    )


def read_bytes(storage_key: str) -> bytes | None:
    """Read an object; return None if it does not exist."""
    key = _validate_key(storage_key)

    if STORAGE_BACKEND == "local":
        directory = _local_storage_dir()
        path = (directory / key).resolve()

        if path.parent != directory or not path.is_file():
            return None

        return path.read_bytes()

    if STORAGE_BACKEND != "s3":
        raise RuntimeError("TRUSTVAULT_STORAGE_BACKEND must be 'local' or 's3'")

    try:
        response = _s3_client().get_object(
            Bucket=_bucket_name(),
            Key=key,
        )
        return response["Body"].read()
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status_code = exc.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if code in ("404", "NoSuchKey", "NotFound") or status_code == 404:
            return None
        raise


def delete_object(storage_key: str) -> None:
    """Delete an object after a failed database operation."""
    key = _validate_key(storage_key)

    if STORAGE_BACKEND == "local":
        directory = _local_storage_dir()
        path = (directory / key).resolve()

        if path.parent == directory:
            path.unlink(missing_ok=True)
        return

    if STORAGE_BACKEND != "s3":
        raise RuntimeError("TRUSTVAULT_STORAGE_BACKEND must be 'local' or 's3'")

    _s3_client().delete_object(
        Bucket=_bucket_name(),
        Key=key,
    )


def copy_object(source_key: str, destination_key: str) -> None:
    """Copy a previous version to a new key without changing the source."""
    source = _validate_key(source_key)
    destination = _validate_key(destination_key)

    if STORAGE_BACKEND == "local":
        content = read_bytes(source)

        if content is None:
            raise FileNotFoundError(source)

        save_bytes(destination, content)
        return

    if STORAGE_BACKEND != "s3":
        raise RuntimeError("TRUSTVAULT_STORAGE_BACKEND must be 'local' or 's3'")

    client = _s3_client()
    client.copy_object(
        Bucket=_bucket_name(),
        Key=destination,
        CopySource={
            "Bucket": _bucket_name(),
            "Key": source,
        },
    )


def new_storage_key() -> str:
    """Generate the same key format used by existing TrustVault uploads."""
    return uuid4().hex
