# TrustVault

## Project Overview

TrustVault is a secure document-sharing platform designed to help users upload, access, and share documents with controlled permissions. It uses authentication, role-based authorization, and audit logging to improve document security and accountability.

## Features

- **User Authentication:** Secure sign-in using Clerk.
- **User Management:** User identity and roles managed through the backend.
- **Document Management:** Upload, list, and download documents.
- **Access Control:** Restrict document access based on permissions and user roles.
- **Document Sharing:** Grant and revoke document permissions.
- **Security Auditing:** Record security-relevant actions, including denied access attempts.
- **File Size Validation:** Limit uploaded files to 10 MiB.
- **Health Checks:** API endpoint for checking backend availability.

## Technology Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI
- **Authentication:** Clerk
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Database Migrations:** Alembic
- **Testing:** pytest
- **Package Management:** pnpm and uv
- **Deployment:** Render

## Project Structure

```text
TrustVault/
├── artifacts/
│   └── trustvault/
│       ├── src/                 # Frontend source code
│       ├── backend/
│       │   ├── app/
│       │   │   ├── routes/      # API endpoints
│       │   │   ├── auth.py      # Authentication
│       │   │   ├── authorization.py
│       │   │   ├── dependencies.py
│       │   │   ├── database.py  # Database access
│       │   │   └── main.py      # FastAPI application
│       │   ├── migrations/      # Database migrations
│       │   └── tests/           # Backend tests
├── docs/                        # Project documentation
├── lib/                         # Shared libraries and API clients
├── PROMPTS.md                   # AI usage and development notes
├── THREATS.md                   # Security threats and mitigations
└── README.md                    # Project overview
```
