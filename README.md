# TrustVault

TrustVault is a secure document-sharing platform for the Thesnovasys hiring challenge. This repository is being built in small, verifiable stages; the current version is only the project foundation, not a finished or security-reviewed document system.

## Current foundation

- `artifacts/trustvault/` — React + TypeScript web application.
- `artifacts/trustvault/backend/` — Python + FastAPI starter API.
- `artifacts/trustvault/backend/tests/` — pytest tests for the starter API.
- `docs/API.md` — current API documentation and implemented routes.
- `THREATS.md` — scope and status of security analysis.
- `PROMPTS.md` — place to record actual development prompts; no history is fabricated.

The shared workspace API uses TypeScript and Express. TrustVault's backend is kept separate because this project brief specifies Python and FastAPI.

## Run locally

The TrustVault web preview is managed by its Replit workflow. To work with the Python API from a terminal:

```bash
cd artifacts/trustvault/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the backend tests from the same directory:

```bash
python -m pytest
```

The starter API exposes `GET /healthz` and FastAPI's interactive API documentation at `/docs`. It does not yet connect to PostgreSQL or implement user accounts, document operations, permissions, or audit logging.

## Planned implementation order

1. Define the PostgreSQL schema and migrations.
2. Choose and integrate managed authentication, then enforce server-side roles and document-level authorization.
3. Add authorization and security tests before document operations.
4. Add private file storage, validated uploads, sharing, search, and audit events.
5. Build the user interface against the implemented API and verify each workflow.

Do not use real documents, credentials, or sensitive data in this starter project.
