# TrustVault Threat Model and Security Notes

## 1. Project Status

TrustVault is a document-sharing security project for the Thesnovasys hiring challenge.

The current version contains a backend security foundation and automated tests. It is not yet a complete document-sharing application and has not undergone a full security review.

This document records identified risks, existing controls, and remaining work. It is not a certification that the application is secure.

## 2. Assets to Protect

- User accounts, identities, and authentication sessions.
- Account roles, including administrator, document owner, and viewer.
- Document contents and metadata.
- Document-specific read and edit permissions.
- Uploaded files and download access.
- Audit records of successful and denied actions.
- Database contents, credentials, and application secrets.

## 3. Trust Boundaries

- **Frontend to backend:** The backend must independently validate every request. Frontend checks alone are not security controls.
- **User to document:** A user must not access another user's documents without explicit permission.
- **Authentication to authorization:** A valid login does not automatically grant access to every document or administrative function.
- **Application to database:** Database access must follow least-privilege principles.
- **Application to file storage:** Files must not be accessible through public or reusable URLs that bypass authorization.
- **Application to audit records:** Ordinary application actions must not be able to alter or erase protected audit history.

## 4. Threats and Mitigations

### T1. Unauthorized Document Access

**Threat:** A user guesses or obtains another document's identifier and attempts to read its contents.

**Required mitigation:** Check authorization on the server for every document request. Do not rely on hidden buttons or frontend restrictions.

**Verification needed:** Test access using different user accounts and document identifiers.

### T2. Privilege Escalation

**Threat:** A user changes a request to claim administrator or owner privileges.

**Required mitigation:** Determine roles from trusted server-side records, not from client-supplied role values.

**Verification needed:** Test attempts to change roles and call administrator-only endpoints without authorization.

### T3. Permission Revocation Failure

**Threat:** A user continues accessing a document after their permission has been revoked.

**Required mitigation:** Check current permissions on each protected request so that revocation takes effect immediately.

**Verification needed:** Grant access, confirm it works, revoke access, and confirm the next request is denied.

### T4. Unsafe File Uploads

**Threat:** Malicious files, oversized uploads, invalid file types, or path-traversal filenames may compromise the application or exhaust resources.

**Required mitigation:** Validate file size, permitted file types, filenames, and storage paths. Consider malware scanning before files are made available.

**Status:** File upload validation and malware scanning remain pending.

### T5. Download Authorization Bypass

**Threat:** A public file URL or predictable storage path allows someone to download a file without permission.

**Required mitigation:** Keep documents in private storage and authorize every download request.

**Status:** Private document storage and download operations remain pending.

### T6. Audit Log Tampering

**Threat:** A user or application operation changes or deletes audit records to hide activity.

**Required mitigation:** Restrict audit-log modifications and document the limits of the protection. Consider independent audit export or external immutable storage.

**Status:** Audit-related controls and tests are present in the current security foundation; independent audit export and a full security review remain pending.

### T7. Information Disclosure

**Threat:** API responses reveal private document details, account information, or whether another user's document exists.

**Required mitigation:** Return only information the requester is authorized to see. Use consistent denial responses where revealing resource existence would be unsafe.

**Verification needed:** Test unauthorized requests and review error messages and API responses.

### T8. Denial of Service

**Threat:** Repeated requests or oversized uploads consume server resources.

**Required mitigation:** Apply request limits, upload-size limits, timeouts, and rate limiting where appropriate.

**Status:** Rate limiting and upload protections remain pending.

### T9. Secret Exposure

**Threat:** Database credentials, authentication secrets, or API keys are committed to source control or exposed in logs.

**Required mitigation:** Store secrets in environment variables or a managed secret store. Exclude local secret files from Git and rotate any exposed credentials.

**Verification needed:** Review tracked files and deployment configuration before publishing.

## 5. Existing Security Foundation

The current project documentation and tests describe controls for:

- Clerk session verification on protected FastAPI routes.
- Server-side account roles and document-scoped permission grants.
- Authorization checks and permission revocation.
- Audit records for selected protected actions and role or permission changes.
- Tests for authentication, authorization, permission restrictions, and audit-related behavior.

These statements describe the current intended foundation and must not be interpreted as proof that every threat above has been eliminated. Review the implementation and test results before making stronger security claims.

## 6. Known Gaps

The following work remains necessary before TrustVault can be considered a complete document-sharing application:

- Private file storage and validated uploads.
- Authorized document downloads.
- Malware scanning.
- Document search and filtering.
- Complete activity and audit views.
- Rate limiting and operational monitoring.
- Additional automated security tests.
- Deployment verification and a full security review.

## 7. Testing Plan

- Verify that unauthenticated requests to protected endpoints are rejected.
- Verify that users cannot grant themselves administrator privileges.
- Verify that users cannot read or edit documents without the required permissions.
- Verify that viewers cannot perform edit operations.
- Verify that revoked permissions deny subsequent requests.
- Verify that audit records are protected against ordinary updates and deletions.
- Add upload, download, search, and audit-view tests when those features are implemented.

## 8. Responsible Use

Do not upload real confidential documents, personal information, or production credentials while the project is incomplete. Do not describe pending features as implemented. Update this threat model whenever new features, security controls, or test results change the project's status.
