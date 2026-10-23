
"""FastAPI application entry point.

Authentication, authorization, database access, and document handling
are implemented in separate modules and verified with tests.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.documents import router as documents_router
from app.routes.security import router as security_router

app = FastAPI(
    title="TrustVault API",
    version="0.1.0",
    description="API for the TrustVault secure document-sharing platform.",
)

# Allow the deployed frontend to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://trustvault-frontend-2d2y.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(security_router)
app.include_router(documents_router)


@app.get("/healthz", tags=["health"])
@app.get("/api/healthz", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
