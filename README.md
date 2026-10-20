# TrustVault

TrustVault is a document-sharing security project for the Thesnovasys hiring challenge. It is being developed in small, verifiable stages.

**Current status:** The backend security foundation and automated tests are present, but the project is not yet a complete document-sharing application or a security-reviewed system.

## Technology stack

- Frontend: React and TypeScript
- Backend: Python and FastAPI
- Database: PostgreSQL
- Database migrations: Alembic
- Authentication: Clerk
- Testing: pytest

## Project structure

- `artifacts/trustvault/` — frontend and backend project files.
- `artifacts/trustvault/backend/` — FastAPI application, database models, migrations and tests.
- `docs/API.md` — API endpoint documentation.
- `docs/SECURITY.md` — security controls and known limitations.
- `THREATS.md` — threat analysis and outstanding risks.
- `PROMPTS.md` — record of genuine development prompts.

## Prerequisites

Install the following before running the backend:

- Python compatible with the backend dependencies
- PostgreSQL
- Git
- A Clerk application and its required configuration, if authentication is being tested

Use the project's dependency files to determine the required package versions.

## Local backend setup

Open a terminal at the repository root and run:

```powershell
cd artifacts/trustvault/backend
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies using the dependency file provided by the backend. For example, if `requirements.txt` exists:

```powershell
python -m pip install -r requirements.txt
```

If the project uses a different dependency manager or file, follow that project's configuration instead.

## Database configuration

Create a local PostgreSQL database and configure the database connection using the environment variable expected by the backend. Configure Clerk credentials and other required settings according to the application configuration.

Do not commit `.env` files, API keys, passwords, session secrets or other credentials to GitHub. Use environment variables or the hosting provider's secret manager.

Before running migrations, confirm that the database connection points to your intended development database.

Apply migrations:

```powershell
python -m alembic upgrade head
```

## Run the API

From `artifacts/trustvault/backend`, run:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

When the server starts successfully, open:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation, if enabled: `http://127.0.0.1:8000/docs`

The API documentation page is not proof that every feature is implemented or secure.

## Run automated tests

From the backend directory:

```powershell
python -m pytest -q
```

Review the test output and investigate any failures. Record the actual result; do not report a test as passing unless it passes in your environment.

## Implemented foundation and limitations

The current project documentation describes authentication, role and permission checks, and audit-related controls in the backend security foundation.

The following features are documented as incomplete and must not be treated as production-ready:

- Private document file storage
- Validated file uploads and authorized downloads
- Malware scanning
- Document search
- Complete activity and administration views
- Full deployment verification and independent security review

Verify each feature against the actual code and tests before describing it as implemented.

## API documentation

See `docs/API.md` for the documented routes and their authorization requirements. Check the code whenever documentation and implementation differ.

## Security

Read `THREATS.md` and `docs/SECURITY.md` before testing the application. Use test data only. Do not upload real private documents or production credentials to an unfinished system.

## Deployment

A working local API does not establish that the application is deployed. Before submission, configure the production database and secrets, deploy the frontend and backend, run migrations, and test the live URL. Document the actual hosting provider, configuration steps, and verified URL once deployment succeeds.

## Development records

`PROMPTS.md` must contain genuine prompts and actual development outcomes. Do not fabricate prompt history, test results, commits, or deployment status.

## Project status

TrustVault is an evolving challenge project. Remaining work and known limitations should be reported honestly in the final submission.
