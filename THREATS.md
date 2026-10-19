# TrustVault security notes

## Status

This is an initial scope note, not a completed threat model and not evidence that TrustVault is secure. The current starter API only reports service health.

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

## Not yet implemented

Authentication, authorization, PostgreSQL schema, migrations, private storage, upload validation, audit logging, and the corresponding security tests are all pending. Do not treat this document as a security review.
