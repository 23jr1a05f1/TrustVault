# TrustVault API

This is the Python/FastAPI service for TrustVault. It is intentionally separate
from the workspace's shared TypeScript/Express API.

## Setup

Use Python 3.11 or newer. Install the project and development dependencies with
your Python package manager, including the `dev` extra from `pyproject.toml`.
The Replit environment for this project already has these packages installed.

## Run

From this directory:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Apply the development database schema and start the API:

```bash
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `/healthz` for health checks, `/docs` for generated API documentation, or
`/api/me` after a Clerk session is available.

## Test

From this directory:

```bash
python -m pytest
```

The first migration creates the TrustVault user, document metadata, document
permission, and append-only audit tables. Protected API routes verify Clerk
sessions and enforce roles from the database. See `docs/SECURITY.md` for
configuration, migration, and test coverage details.
