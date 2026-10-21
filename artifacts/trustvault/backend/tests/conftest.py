
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import anyio
import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import AuthenticatedIdentity, require_clerk_identity
from app.config import Settings, get_settings
from app.database import get_db
from app.main import app
from app.models import AuditEvent, Base, Document, DocumentPermission, User


class TestApiClient:
    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async def send_request() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://trustvault.test",
            ) as client:
                return await client.request(method, path, json=body)

        return anyio.run(send_request, backend="asyncio")

    def upload(
        self,
        path: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> httpx.Response:
        async def send_request() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://trustvault.test",
            ) as client:
                return await client.post(
                    path,
                    files={"file": (filename, content, content_type)},
                    data={"category": "test"},
                )

        return anyio.run(send_request, backend="asyncio")


@dataclass
class SecurityTestEnvironment:
    client: TestApiClient
    auth_context: dict[str, str]
    session_factory: sessionmaker[Session]

    def sign_in_as(self, clerk_id: str) -> None:
        self.auth_context["clerk_id"] = clerk_id

    def add_user(self, clerk_id: str, role: str = "member") -> UUID:
        with self.session_factory() as db:
            user = User(clerk_id=clerk_id, role=role)
            db.add(user)
            db.commit()
            return user.id

    def add_document(
        self,
        owner_id: UUID,
        name: str = "Tax return.pdf",
    ) -> UUID:
        with self.session_factory() as db:
            document = Document(
                owner_id=owner_id,
                name=name,
                category="tax",
                content_type="application/pdf",
                size_bytes=128,
                storage_key=f"test/{uuid4()}",
            )
            db.add(document)
            db.commit()
            return document.id

    def add_permission(
        self,
        document_id: UUID,
        user_id: UUID,
        granted_by_id: UUID,
        access_level: str = "read",
    ) -> None:
        with self.session_factory() as db:
            db.add(
                DocumentPermission(
                    document_id=document_id,
                    user_id=user_id,
                    granted_by_id=granted_by_id,
                    access_level=access_level,
                )
            )
            db.commit()

    def audit_events(self) -> list[AuditEvent]:
        with self.session_factory() as db:
            return list(
                db.scalars(
                    select(AuditEvent).order_by(
                        AuditEvent.created_at,
                        AuditEvent.id,
                    )
                )
            )

    def user(self, user_id: UUID) -> User | None:
        with self.session_factory() as db:
            return db.get(User, user_id)


@pytest.fixture
def test_env() -> SecurityTestEnvironment:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: Any,
        _connection_record: Any,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TRIGGER trustvault_test_audit_no_update
            BEFORE UPDATE ON trustvault_audit_events
            BEGIN
                SELECT RAISE(ABORT, 'audit events are append-only');
            END;
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TRIGGER trustvault_test_audit_no_delete
            BEFORE DELETE ON trustvault_audit_events
            BEGIN
                SELECT RAISE(ABORT, 'audit events are append-only');
            END;
            """
        )

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )

    auth_context = {"clerk_id": "user-test-default"}

    test_settings = Settings(
        clerk_secret_key=SecretStr("sk_test_not_used"),
        clerk_authorized_parties="https://trustvault.test",
        database_url=SecretStr("sqlite+pysqlite://"),
    )

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[require_clerk_identity] = lambda: (
        AuthenticatedIdentity(clerk_id=auth_context["clerk_id"])
    )

    try:
        yield SecurityTestEnvironment(
            client=TestApiClient(),
            auth_context=auth_context,
            session_factory=factory,
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
