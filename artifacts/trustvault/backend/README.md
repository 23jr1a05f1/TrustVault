# TrustVault API

This is the Python/FastAPI backend service for TrustVault. It handles authentication, authorization, document operations, and security auditing.

## Requirements

- Python 3.11 or newer
- `uv` for Python dependency management
- A configured PostgreSQL database
- Clerk authentication configuration

## Setup

Run the following commands from this directory:

```bash
uv sync
```

Configure the required database and Clerk environment variables locally. Never commit secrets or `.env` files.

## Database Migration

Apply the database migrations before starting the API:

```bash
python -m alembic upgrade head
```

## Run the API

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `/healthz` — API health check
- `/docs` — interactive API documentation
- `/api/me` — current authenticated user's information; requires a valid Clerk session

## Run Tests

```bash
python -m pytest -q
```

## Security Notes

The backend verifies Clerk sessions and enforces authorization using database roles and document permissions. It also records security-relevant audit events.

The initial database migration creates tables for users, document metadata, document permissions, and audit records.

See `docs/SECURITY.md` for additional details about security configuration, migrations, and test coverage.

Use non-sensitive test documents until production storage and deployed document workflows have been verified.