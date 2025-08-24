from app.models import models
from app.core.config import settings


def test_get_user_roles(client, db_session):
    settings.KEYCLOAK_BYPASS = True

    admin = models.User(keycloak_id='adm2', first_name='Admin2', email='adm2@example.com')
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    # create another user and assign roles
    u = models.User(keycloak_id='uroles', first_name='Roley', email='roles@example.com')
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    # assign two roles
    r1 = models.Role(name='agent')
    r2 = models.Role(name='activity-manager')
    db_session.add_all([r1, r2])
    db_session.commit()
    db_session.add(models.UserRole(user_id=u.id, role_id=r1.id))
    db_session.add(models.UserRole(user_id=u.id, role_id=r2.id))
    db_session.commit()

    headers = {'x-test-user': str(admin.id)}
    r = client.get(f'/admin/users/{u.id}/roles', headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert 'agent' in body and 'activity-manager' in body
