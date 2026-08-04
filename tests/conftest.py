import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app import gitstore
from app.models import Tenant, User
from app.auth import pwd_context

# Reuse the SAME Supabase connection string your app already uses -- tests
# are isolated by Postgres *schema*, not by a separate database, since
# hosted Supabase gives one database per project.
DATABASE_URL = os.environ["DATABASE_URL"]
TEST_SCHEMA = "test_smartverify"

# schema_translate_map rewrites every unqualified table reference (i.e. every
# model in Base.metadata, none of which declare an explicit schema) to live
# under TEST_SCHEMA instead of "public" -- so create_all/drop_all/queries
# during tests never touch your real seeded tables.
engine = create_engine(DATABASE_URL).execution_options(
    schema_translate_map={None: TEST_SCHEMA}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
        conn.commit()


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield session

    session.close()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    app.dependency_overrides.clear()


@pytest.fixture()
def git_repo(tmp_path, monkeypatch):
    repo_path = tmp_path / "git_repo"
    monkeypatch.setattr(gitstore, "GIT_REPO_PATH", repo_path)
    gitstore.init_repo()
    return repo_path


@pytest.fixture()
def client(db_session, git_repo):
    return TestClient(app)


@pytest.fixture()
def seeded_data(db_session):
    acme_prod = Tenant(customer_name="Acme Corp", name="Acme Production", slug="acme-prod-test")
    globex_prod = Tenant(customer_name="Globex Inc", name="Globex Production", slug="globex-prod-test")
    db_session.add_all([acme_prod, globex_prod])
    db_session.flush()

    alice = User(username="alice_test", password_hash=pwd_context.hash("alicepw"))
    alice.tenants = [acme_prod]

    carol = User(username="carol_test", password_hash=pwd_context.hash("carolpw"))
    carol.tenants = [globex_prod]

    db_session.add_all([alice, carol])
    db_session.commit()

    return {"acme_prod": acme_prod, "globex_prod": globex_prod, "alice": alice, "carol": carol}


@pytest.fixture()
def login(client):
    def _login(username: str, password: str) -> dict:
        resp = client.post("/api/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['token']}"}
    return _login