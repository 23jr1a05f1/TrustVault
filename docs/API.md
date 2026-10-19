# TrustVault API

FastAPI generates interactive API documentation from the running service:

- `/docs` — interactive Swagger UI
- `/redoc` — ReDoc reference
- `/openapi.json` — machine-readable OpenAPI document

## Implemented endpoints

| Method | Path | Purpose | Access |
| --- | --- | --- | --- |
| `GET` | `/healthz` | Check that the API process is responding | Public service health |
| `GET` | `/api/me` | Return the signed-in user's server-stored account role | Clerk session |
| `GET` | `/api/documents/{document_id}` | Read document metadata | Admin, owner, editor, or viewer |
| `POST` | `/api/documents/{document_id}/permissions` | Grant or update a document-scoped permission | Admin or document owner |
| `DELETE` | `/api/documents/{document_id}/permissions/{target_user_id}` | Revoke a document permission | Admin or document owner |
| `PATCH` | `/api/users/{target_user_id}/role` | Change a server-stored account role | Admin |

All routes except health require a verified Clerk session. Unknown and
unauthorized document IDs return the same `404`. Successful and denied
protected actions are recorded in the audit table. File upload, download,
search, and activity-feed endpoints are not implemented yet.
