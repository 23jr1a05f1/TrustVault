# TrustVault security foundation

This documents the current security implementation. It is not a penetration
test, compliance assessment, or claim that the unfinished application is ready
for sensitive documents.

## Authentication and account roles

- Clerk is the managed identity provider. FastAPI verifies session tokens with
  Clerk's backend SDK and checks the token's authorized party against an
  explicit allowlist or Replit-provided app domains.
- The Express workspace API proxies Clerk's Frontend API in production. The
  TrustVault FastAPI service independently verifies sessions on protected
  routes.
- Local TrustVault users are created from the verified Clerk `sub` claim.
  New accounts receive the server-stored `member` role by default.
- `admin` is a server-stored role. Client request bodies and Clerk public
  metadata cannot set it. A trusted operator can bootstrap an administrator
  with `TRUSTVAULT_ADMIN_CLERK_IDS`, a comma-separated list of Clerk user IDs.
  Role changes are audited.

## Document access

Roles are resolved from the current PostgreSQL rows for every request:

- `admin`: can read documents and manage document permissions.
- `owner`: can read their own documents and manage their permissions.
- `editor`: a document-scoped `edit` grant; can read, with edit routes to be
  implemented alongside document editing.
- `viewer`: a document-scoped `read` grant; read-only.

Unknown and unauthorized document IDs use the same `404` response. Permission
revocation deletes the grant, so the next request is denied without relying on
an authorization cache. No file download endpoint is implemented yet.

## Audit trail

Successful reads, permission changes, role changes, and denied protected
actions are recorded in `trustvault_audit_events`. PostgreSQL blocks `UPDATE`
and `DELETE` on this table with a trigger. This protects against ordinary
application writes; a database owner or superuser can still alter the schema or
data. Audit rows are not cryptographically signed or exported to an independent
immutable log service.

## Schema and migration

The initial schema is managed by Alembic in `backend/migrations/`. Apply it to
the development database from `artifacts/trustvault/backend` with:

```bash
python -m alembic upgrade head
```

Do not run this against production by hand. Production schema rollout must be
coordinated with the deployment process.

## Verified test coverage

The security tests cover missing sessions, least-privilege account creation,
role escalation denial, admin role changes, document ID concealment,
permission grants and immediate revocation, viewer restrictions, and audit
immutability. Tests replace the Clerk identity dependency with controlled
test identities; they do not claim to test a live Clerk login.

Private file storage, upload validation, download authorization, malware
scanning, rate limits, operational monitoring, and a full security review are
still outstanding.
