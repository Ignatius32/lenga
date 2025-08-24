import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.core.database import Base
from app import models


@pytest.fixture()
def client_with_user():
    # ensure bypass mode enabled
    settings.KEYCLOAK_BYPASS = True
    # create tables and a minimal user to impersonate
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # avoid duplicate insertion if a previous test run created this user
        u = db.query(models.User).filter(models.User.keycloak_id == 'test-user').first()
        if not u:
            u = models.User(keycloak_id='test-user', first_name='Test', last_name='User', email='test@example.com')
            db.add(u)
            db.commit()
            db.refresh(u)
        # ensure admin role exists and assign it to the user so admin endpoints are accessible
        role = db.query(models.Role).filter(models.Role.name == 'admin').first()
        if not role:
            role = models.Role(name='admin')
            db.add(role)
            db.commit()
            db.refresh(role)
        from app.models.models import UserRole
        ur = db.query(UserRole).filter(UserRole.user_id == u.id, UserRole.role_id == role.id).first()
        if not ur:
            db.add(UserRole(user_id=u.id, role_id=role.id))
            db.commit()
        client = TestClient(app)
        yield client, u.id
    finally:
        db.close()


def test_admin_routes_not_404(client_with_user):
    client, uid = client_with_user
    headers = {'x-test-user': str(uid)}

    # basic API endpoints - should not be 404
    for path in ['/admin/queues', '/admin/users', '/admin/agent_assignments', '/admin/queue_permissions']:
        r = client.get(path, headers=headers)
        assert r.status_code != 404, f"{path} returned 404 (body={r.text})"

    # UI endpoints (minimal HTML)
    r = client.get('/admin/ui/users', headers=headers)
    assert r.status_code == 200

    r = client.get('/admin')
    # index should return HTML content
    assert r.status_code == 200
    assert 'text/html' in r.headers.get('content-type', '')
