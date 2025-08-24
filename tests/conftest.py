import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.core.config import settings as app_settings


TEST_DATABASE_URL = "sqlite:///./test_institution_manager.db"


engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope='session')
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope='function')
def db_session(db_engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope='function')
def client(db_session, monkeypatch):
    # override get_db to use the testing session
    def override_get_db():
        # create a new Session bound to the same connection used by the test's db_session
        db = TestingSessionLocal(bind=db_session.bind)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    # enable bypass for tests
    app_settings.KEYCLOAK_BYPASS = True
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    # for unit tests we can return a fake header; actual jwt validation is mocked in tests
    return {"Authorization": "Bearer faketoken"}
