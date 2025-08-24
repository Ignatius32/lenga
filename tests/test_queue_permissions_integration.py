import json

from app.models import models
from app.core.config import settings


def create_user(session, keycloak_id='u-1', email='u@example.com'):
    u = models.User(keycloak_id=keycloak_id, email=email)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_queue_permissions_allow_and_revoke(client, db_session):
    # ensure bypass for test-client is enabled in conftest fixture; set again to be explicit
    settings.KEYCLOAK_BYPASS = True

    # create admin and normal user
    admin = create_user(db_session, keycloak_id='admin-qp', email='admin-qp@example.com')
    user = create_user(db_session, keycloak_id='user-qp', email='user-qp@example.com')

    # give admin role
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    admin_headers = {'x-test-user': str(admin.id)}
    user_headers = {'x-test-user': str(user.id)}

    # create a queue as admin
    r = client.post('/admin/queues', json={'name': 'Billing', 'description': 'Billing queue'}, headers=admin_headers)
    assert r.status_code == 200
    q = r.json()

    # create a group and add user to the group
    g = models.Group(name='Billing Users')
    db_session.add(g)
    db_session.commit()
    db_session.add(models.UserGroup(user_id=user.id, group_id=g.id))
    db_session.commit()

    # initially, user should NOT be able to create a ticket in the queue
    payload = {'subject': 'Test bill', 'description': 'Please help', 'queue_id': q['id']}
    r = client.post('/tickets/', json=payload, headers=user_headers)
    assert r.status_code == 403

    # grant group permission to queue as admin
    r = client.post('/admin/queue_permissions', json={'group_id': g.id, 'queue_id': q['id']}, headers=admin_headers)
    assert r.status_code == 200

    # now user should be able to create ticket
    r = client.post('/tickets/', json=payload, headers=user_headers)
    assert r.status_code == 200
    t = r.json()
    assert t['subject'] == payload['subject']
    assert t['current_queue_id'] == q['id']

    # revoke permission (use request with json because TestClient.delete() may not accept json kw)
    r = client.request('DELETE', '/admin/queue_permissions', json={'group_id': g.id, 'queue_id': q['id']}, headers=admin_headers)
    assert r.status_code == 200

    # after revoke, user should be forbidden again
    r = client.post('/tickets/', json=payload, headers=user_headers)
    assert r.status_code == 403
