# TrustVault Security Foundation

This document describes implemented security controls and known limitations. It is not a penetration test, compliance assessment, or claim that the application is production-ready for sensitive documents.

## Authentication and Account Roles

- Clerk is the managed identity provider. FastAPI verifies session tokens using Clerk's backend SDK and checks authorized parties against configured values.
- The TrustVault FastAPI service independently verifies sessions on protected routes.
- Local TrustVault users are created from verified Clerk identities. New accounts receive the server-stored `member` role by default.
- The `admin` role is stored server-side. Client request bodies and Clerk public metadata cannot directly assign it. Trusted operators can configure bootstrap administrators using `TRUSTVAULT_ADMIN_CLERK_IDS`.
- Role changes and relevant security events are audited.

## Document Access

Document access is checked on the server using current database records:

- `admin`: can read documents and manage document permissions.
- `owner`: can read their own documents and manage their permissions.
- `editor`: a document-scoped `edit` grant; can read, but document editing routes are not yet implemented.
- `viewer`: a document-scoped `read` grant; read-only.

The document API supports private file uploads and authorized downloads.

- Uploads are limited to 10 MiB.
- Files are stored using server-generated storage keys rather than user-supplied filesystem paths.
- Download requests check current document permissions.
- Unauthorized and unknown document downloads return `404` responses to reduce document-ID enumeration.
- Permission revocation removes the grant, so subsequent download requests are denied.
- Upload and download outcomes are recorded in the audit trail.

The current implementation still needs production storage and deployment verification. Local filesystem storage may not persist across redeployments or be shared across multiple server instances. Do not use real sensitive documents until production storage, backups, access controls, and deployment behavior have been verified.

## Audit Trail

Relevant document operations, permission changes, role changes, and denied protected actions are recorded in `trustvault_audit_events`.

The PostgreSQL migration installs a trigger that blocks ordinary `UPDATE` and `DELETE` operations on audit events. This is not protection against a database owner or superuser changing the schema or data. The audit trail is not cryptographically signed or exported to an independently controlled immutable logging service.

## Schema and Migration

The database schema is managed by Alembic in `artifacts/trustvault/backend/migrations/`.

From the backend directory, apply migrations to the intended development database with:

```bash
python -m alembic upgrade head
```

Confirm the database connection before running migrations. Production migrations must be coordinated with deployment and backup procedures.

## Verified Test Coverage

The automated test suite currently passes **16 tests** in the local development environment.

Coverage includes authentication-related security behavior, least-privilege account creation, role escalation denial, document permission management and revocation, audit immutability, private file upload, authorized download, denial of unauthorized downloads, and rejection of oversized uploads.

Tests use controlled test identities and a test database. They do not establish that live Clerk authentication, production PostgreSQL, deployed storage, or the production deployment has been independently verified.

## Known Limitations

- Malware scanning is not implemented.
- Document editing and complete document search are not verified as implemented.
- Production storage durability, backups, and multi-instance behavior require verification.
- Independent audit export, operational monitoring, rate limiting, and a full security review remain outstanding.
- Deployment and live URL verification remain outstanding until tested against the actual deployed application.
