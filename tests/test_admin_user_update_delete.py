import pytest

from app.models import models
from app.core.config import settings


def test_admin_user_update_and_delete(client, db_session):
    settings.KEYCLOAK_BYPASS = True

    # create an admin user and assign admin role via DB
    admin = models.User(keycloak_id='adm1', first_name='Admin', last_name='One', email='adm1@example.com')
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    headers = {'x-test-user': str(admin.id)}

    # create a regular user via admin endpoint
    payload = {'keycloak_id': 'u99', 'first_name': 'User', 'last_name': '99', 'email': 'u99@example.com'}
    r = client.post('/admin/users', json=payload, headers=headers)
    assert r.status_code == 200
    user = r.json()
    uid = user['id']

    # update the user
    r = client.put(f'/admin/users/{uid}', json={'first_name': 'Updated', 'email': 'new@example.com'}, headers=headers)
    assert r.status_code == 200
    u2 = r.json()
    assert u2['first_name'] == 'Updated'
    assert u2['email'] == 'new@example.com'

    # delete should succeed when there are no references
    r = client.delete(f'/admin/users/{uid}', headers=headers)
    assert r.status_code == 200
    assert r.json().get('status') == 'deleted'

    # create a user and a ticket referencing them, deletion should fail
    uref = models.User(keycloak_id='uref', first_name='Ref', last_name='One', email='ref@example.com')
    db_session.add(uref)
    db_session.commit()
    db_session.refresh(uref)
    # create queue and ticket referencing uref
    q = models.Queue(name='QX')
    db_session.add(q)
    db_session.commit()
    t = models.Ticket(subject='t', client_user_id=uref.id, current_queue_id=q.id)
    db_session.add(t)
    db_session.commit()

    r = client.delete(f'/admin/users/{uref.id}', headers=headers)
    assert r.status_code == 400

