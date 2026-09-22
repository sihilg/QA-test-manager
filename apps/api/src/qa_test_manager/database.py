from collections.abc import Iterator
from os import environ

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./qa-test-manager.db"


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or environ.get("QA_TEST_MANAGER_DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_engine(url)

    if url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    return engine


def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
