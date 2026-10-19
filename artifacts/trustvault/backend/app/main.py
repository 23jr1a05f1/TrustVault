"""FastAPI application entry point.

Keep request handlers small. Authentication, authorization, database access,
and document handling will be added in separate modules and verified with tests.
"""

from fastapi import FastAPI

app = FastAPI(
    title="TrustVault API",
    version="0.1.0",
    description="API for the TrustVault secure document-sharing platform.",
)


@app.get("/healthz", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
