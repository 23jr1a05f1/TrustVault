# TrustVault API

FastAPI generates interactive API documentation from the running service:

- `/docs` — interactive Swagger UI
- `/redoc` — ReDoc reference
- `/openapi.json` — machine-readable OpenAPI document

## Implemented endpoint

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| `GET` | `/healthz` | Check that the API process is responding | Public service health |

This is only the starter contract. Authentication, users, documents, permissions,
search, downloads, and audit routes have not been implemented.
