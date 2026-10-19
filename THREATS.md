# TrustVault security notes

## Status

This is an evolving scope note, not a completed threat model and not evidence that TrustVault is secure. The current API has a security foundation but no private document storage or file operations.

## Assets and boundaries to address

- User identities, authentication sessions, and role assignments.
- Document contents, metadata, and per-document permissions.
- Private file storage and the API boundary used to read or download files.
- Audit events for successful and denied actions.
- PostgreSQL data and configuration secrets.

## Risks requiring implementation and tests

- Guessable document identifiers or missing document-level checks could expose another user's files.
- Client-supplied roles or frontend-only checks could allow privilege escalation.
- Revoked permissions must stop authorizing subsequent requests.
- Unsafe or oversized uploads could cause malware exposure, resource exhaustion, or path traversal.
- A reusable public file URL could bypass API authorization.
- Ordinary application writes must not be able to rewrite or erase audit history; the chosen design and its limits must be documented.

## Implemented and tested in the security foundation

- Clerk session verification on protected FastAPI routes with an authorized-party check.
- Database-backed account roles and document-scoped read/edit grants.
- Denial of document ID enumeration, server-side authorization, and immediate
  effect of permission revocation.
- Audit rows for protected access and role/permission changes; PostgreSQL
  rejects ordinary `UPDATE` and `DELETE` operations on audit rows.
- Unit/API tests cover missing sessions, role escalation, grants/revocation,
  viewer restrictions, document ID concealment, and audit immutability.

## Not yet implemented

Private storage, upload validation, download authorization, malware scanning,
search, rate limits, independent audit export, and a full security review remain
pending. Do not treat this document as a security review.
