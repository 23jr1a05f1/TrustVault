# TrustVault API

This is the Python/FastAPI service for TrustVault. It is intentionally separate
from the workspace's shared TypeScript/Express API.

## Setup

Use Python 3.11 or newer. Install the project and development dependencies with
your Python package manager, including the `dev` extra from `pyproject.toml`.
The Replit environment for this project already has these packages installed.

## Run

From this directory:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `/healthz` for the starter health check or `/docs` for the generated API
documentation.

## Test

From this directory:

```bash
python -m pytest
```

The current API has no database connection and no protected document routes.
