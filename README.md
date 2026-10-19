# TrustVault

TrustVault is a secure document-sharing platform for the Thesnovasys hiring challenge. This repository is being built in small, verifiable stages; the current version has a security foundation, but is not a finished or security-reviewed document system.

## Current foundation

- `artifacts/trustvault/` — React + TypeScript web application.
- `artifacts/trustvault/backend/` — Python + FastAPI API, PostgreSQL models, and Alembic migrations.
- `artifacts/trustvault/backend/tests/` — pytest tests for authentication and authorization behavior.
- `docs/API.md` — current API documentation and implemented routes.
- `docs/SECURITY.md` — implemented security controls and remaining limitations.
- `THREATS.md` — scope and status of security analysis.
- `PROMPTS.md` — place to record actual development prompts; no history is fabricated.

The shared workspace API uses TypeScript and Express. TrustVault's backend is kept separate because this project brief specifies Python and FastAPI.

## Run locally

The TrustVault web preview is managed by its Replit workflow. To work with the Python API from a terminal:

```bash
cd artifacts/trustvault/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Apply the development database migration and run the backend tests from the same directory:

```bash
python -m alembic upgrade head
python -m pytest
```

The API exposes health, Clerk-protected account and document-metadata routes,
document permission management, and admin-only account-role updates. Document
file storage, upload/download, search, and the user interface are not complete.
See `docs/SECURITY.md` before using real or sensitive data.

## Planned implementation order

1. Complete the user interface and route it to the protected API.
2. Add private file storage, validated uploads/downloads, malware scanning, and search.
3. Add activity views and operational monitoring, then conduct a full security review.

Do not use real documents, credentials, or sensitive data in this starter project.
