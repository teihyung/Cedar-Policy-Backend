import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app import models, gitstore  # noqa: F401 -- registers models on Base.metadata
from app.routers import health, auth_routes, tenants, policy_files

app = FastAPI(title="Cedar Policy Backend", version="0.1.0")

# Browsers block cross-origin requests by default (your React dev server on
# :5173/:3000 talking to this API on :8000 counts as cross-origin). This
# whitelists dev origins; override via env var for staging/prod domains.
_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],   # must include Authorization for the bearer token
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    gitstore.init_repo()


app.include_router(health.router)
app.include_router(auth_routes.router)
app.include_router(tenants.router)
app.include_router(policy_files.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)