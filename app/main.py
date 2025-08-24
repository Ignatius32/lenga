from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from app.core.config import settings
from app.core.database import engine
from app.core.database import Base
from app.api import logistics, tickets, agents, activities, attachments, admin
from app.api import users

app = FastAPI(title="Institution Manager - Phase 1")

# OpenAPI security scheme
app.openapi_schema = None
security_scheme = {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}



@app.on_event("startup")
def on_startup():
    # For development only: create tables if they don't exist. Alembic is recommended for migrations.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(logistics.router)
app.include_router(tickets.router)
app.include_router(agents.router)
app.include_router(activities.router)
app.include_router(attachments.router)
app.include_router(admin.router)
app.include_router(users.router)

# Serve the admin SPA static files under /admin/static to avoid shadowing admin API routes
app.mount("/admin/static", StaticFiles(directory="./www", html=True), name="admin_static")

# Serve the SPA entry at /admin (returns index.html)
from fastapi.responses import FileResponse


@app.get('/admin', response_class=FileResponse)
def admin_index():
    return FileResponse('./www/index.html')

