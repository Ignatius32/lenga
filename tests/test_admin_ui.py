from app.models import models
from app.core.config import settings


def test_admin_ui_pages(client, db_session):
    settings.KEYCLOAK_BYPASS = True
    admin = models.User(keycloak_id='uiadm', first_name='UiAdmin', email='uiadm@example.com')
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    headers = {'x-test-user': str(admin.id)}
    r = client.get('/admin/ui/users', headers=headers)
    assert r.status_code == 200
    assert '<h1>Users</h1>' in r.text

    # create user and open detail
    u = models.User(keycloak_id='someone', first_name='Someone', email='someone@example.com')
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    r2 = client.get(f'/admin/ui/users/{u.id}', headers=headers)
    assert r2.status_code == 200
    assert f'User {u.id}' in r2.text
