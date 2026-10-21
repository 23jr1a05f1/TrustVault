# TrustVault — Secure Document Sharing

TrustVault is a document-sharing security project developed for the Snovasys hiring challenge. It focuses on server-side authorization, private document handling, permission management, and security audit records.

**Project status:** The backend security foundation and core document upload/download endpoints are implemented, with automated tests. Production deployment, durable storage verification, and independent security review remain outstanding.

## Technology Stack

- **Frontend:** React and TypeScript
- **Backend:** Python and FastAPI
- **Database:** PostgreSQL
- **Database migrations:** Alembic
- **Authentication:** Clerk
- **ORM:** SQLAlchemy
- **Testing:** pytest

## Features Implemented

- Clerk-based session verification on protected backend routes.
- Server-side account roles and document-scoped permissions.
- Document permission grants and revocation.
- Private document uploads with a 10 MiB application-level size limit.
- Downloads authorized against current server-side permissions.
- Denial of unauthorized document downloads.
- Audit events for selected security and document operations.
- Database protections against ordinary updates and deletions of audit events.
- Automated tests for security controls and document operations.

These features have automated test coverage, but this does not establish that the entire application is production-ready.

## Project Structure

- `artifacts/trustvault/` — application workspace.
- `artifacts/trustvault/backend/` — FastAPI application, models, migrations, and tests.
- `docs/API.md` — API documentation.
- `docs/SECURITY.md` — implemented controls and security limitations.
- `THREATS.md` — threat model and remaining risks.
- `PROMPTS.md` — development prompt and verification record.

## Prerequisites

For backend development, install:

- Python compatible with the backend project configuration.
- `uv`, the Python project and dependency manager.
- PostgreSQL for running the application against a database.
- A Clerk application and the required authentication configuration.
- Git.

Frontend prerequisites and commands should follow the package configuration in the application workspace.

## Run the Backend Locally

Open PowerShell at the repository root.

Change to the backend directory:

```powershell
cd artifacts/trustvault/backend
```

Install and synchronize the backend dependencies using the project's lockfile:

```powershell
uv sync
```

Activate the virtual environment in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Configure the required environment variables using the backend settings and a local `.env` file or environment configuration. Set up a development PostgreSQL database and the required Clerk settings before starting the API.

**Never commit `.env` files, API keys, database passwords, authentication secrets, or real private documents.**

Apply database migrations to the intended development database:

```powershell
python -m alembic upgrade head
```

Start the API:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

When startup succeeds, the API is available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`, if enabled.

A running API or accessible documentation page does not prove that all application features work correctly.

## Run Automated Tests

From `artifacts/trustvault/backend`, activate the project's virtual environment if needed, then run:

```powershell
python -m pytest -q
```

The most recent test run before this documentation update reported:

```text
16 passed in 0.65s
```

Rerun the tests after code changes and record the actual result. The test suite uses controlled test identities and a test database; passing tests do not verify live Clerk authentication or production infrastructure.

## Security and Limitations

Important remaining work includes:

- Malware scanning and a defined permitted-file-type policy.
- Verification of persistent production file storage, backups, and recovery.
- Rate limiting, quotas, operational monitoring, and alerting.
- Complete document search, editing, and administrative activity views.
- Independent audit export and a full security review.
- Verification of production authentication, database configuration, and deployment.

The local filesystem storage used by the current implementation may not persist across redeployments or be shared between server instances. Production storage must be evaluated and configured before relying on the service for important documents.

Read `docs/SECURITY.md` and `THREATS.md` before testing or deploying the application. Use non-sensitive test data until production security and storage have been verified.

## Deployment

**Deployment status:** Not verified.

Before submitting a live application:

1. Choose a host that supports the backend, database, and required storage behavior.
2. Configure production environment variables and authentication settings securely.
3. Provision the production database and apply migrations through the deployment process.
4. Configure durable private document storage.
5. Deploy the frontend and backend with the correct API configuration.
6. Test the deployed site in a private browser window.
7. Verify authentication, document uploads, authorized downloads, permission revocation, and error handling using non-sensitive test accounts.
8. Record the actual deployment provider and verified live URL.

Do not report a live deployment as successful until the URL has been tested from a separate browser session.

## Development Records

`PROMPTS.md` records genuine AI-assisted development work and its actual verification results. Keep it updated as significant tasks are completed. Do not invent prompts, test outcomes, commit history, or deployment status.

## License and Challenge Submission

Add a license only if one has been selected for the project. Before submission, verify that the GitHub repository is accessible to judges, the required links work, and the project description accurately reflects the implemented features and outstanding limitations.
