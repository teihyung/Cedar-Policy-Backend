import os
from dotenv import load_dotenv
from app.db import Base, engine, SessionLocal
from app.models import Tenant, User
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        acme_prod = Tenant(customer_name="Acme Corp", name="Acme Production", slug="acme-prod")
        acme_staging = Tenant(customer_name="Acme Corp", name="Acme Staging", slug="acme-staging")
        globex_prod = Tenant(customer_name="Globex Inc", name="Globex Production", slug="globex-prod")
        db.add_all([acme_prod, acme_staging, globex_prod])
        db.flush()

        alice = User(username="alice", password_hash=hash_password(os.environ["SEED_ALICE_PASSWORD"]))
        alice.tenants = [acme_prod, acme_staging]

        bob = User(username="bob", password_hash=hash_password(os.environ["SEED_BOB_PASSWORD"]))
        bob.tenants = [acme_prod]

        carol = User(username="carol", password_hash=hash_password(os.environ["SEED_CAROL_PASSWORD"]))
        carol.tenants = [globex_prod]

        db.add_all([alice, bob, carol])
        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()