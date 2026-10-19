# TrustVault

TrustVault is a secure document-sharing platform being built in stages for the Thesnovasys hiring challenge.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm --filter @workspace/trustvault run dev` — run the React web app
- From `artifacts/trustvault/backend`, `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` — run the FastAPI starter
- From `artifacts/trustvault/backend`, `python -m pytest` — run the FastAPI tests
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- TrustVault frontend: React + TypeScript + Vite
- Shared workspace API: Express 5 (not the TrustVault-specific API)
- TrustVault API: Python 3.11 + FastAPI
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/trustvault/src/` — TrustVault React frontend (currently scaffold only)
- `artifacts/trustvault/backend/` — TrustVault FastAPI starter and pytest tests
- `docs/API.md` — current API surface and documentation locations
- `README.md`, `THREATS.md`, and `PROMPTS.md` — project overview, security scope, and truthful prompt record

## Architecture decisions

- Keep TrustVault's FastAPI service separate from the workspace's existing Express API because the brief explicitly requires Python/FastAPI.
- The starter API exposes only health; authentication, database schema, document access, and audit behavior are not implemented yet.

## Product

Planned: role-based access for administrators, document owners, and viewers; private document storage; per-document permissions; search; and auditable activity. These capabilities must not be described as available until implemented and verified.

## User preferences

- Keep the project readable for a beginner and suitable for explaining in an interview.
- Build and verify in stages; do not implement everything in one unverified step.

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
