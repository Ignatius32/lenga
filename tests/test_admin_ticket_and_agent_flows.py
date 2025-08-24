import json

from app.models import models
from app.core.config import settings


def create_user(session, keycloak_id='u-1', email='u@example.com'):
    u = models.User(keycloak_id=keycloak_id, email=email)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_admin_ticket_type_and_agent_assignment(client, db_session):
    settings.KEYCLOAK_BYPASS = True

    # create admin and agent users
    admin = create_user(db_session, keycloak_id='admin-tt', email='admin-tt@example.com')
    agent = create_user(db_session, keycloak_id='agent-tt', email='agent-tt@example.com')

    # give admin role
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    headers = {'x-test-user': str(admin.id)}

    # create a queue
    r = client.post('/admin/queues', json={'name': 'Support', 'description': 'Support queue'}, headers=headers)
    assert r.status_code == 200
    q = r.json()

    # create a group and add agent to the group
    g = models.Group(name='Support Team')
    db_session.add(g)
    db_session.commit()
    db_session.add(models.UserGroup(user_id=agent.id, group_id=g.id))
    db_session.commit()

    # allow group to access queue (queue_permission)
    r = client.post('/admin/queue_permissions', json={'group_id': g.id, 'queue_id': q['id']}, headers=headers)
    assert r.status_code == 200

    # create a ticket type assigned to the queue and allowed for the group
    payload = {'queue_id': q['id'], 'name': 'Issue', 'allowed_group_ids': [g.id], 'fields': [{'name': 'Severity', 'field_type': 'select', 'options': ['Low','High']}]}
    r = client.post('/admin/ticket_types', json=payload, headers=headers)
    assert r.status_code == 200
    tt = r.json()
    assert tt['queue_id'] == q['id']
    assert g.id in tt['allowed_group_ids']

    # assign agent to queue
    r = client.post('/admin/agents/assign', json={'agent_user_id': agent.id, 'queue_id': q['id'], 'access_level': 'full'}, headers=headers)
    assert r.status_code == 200
    aa = r.json()
    assert aa['agent_user_id'] == agent.id
    assert aa['queue_id'] == q['id']

    # list agent assignments
    r = client.get('/admin/agent_assignments', headers=headers)
    assert r.status_code == 200
    arr = r.json()
    assert any(a['agent_user_id'] == agent.id and a['queue_id'] == q['id'] for a in arr)

    # unassign agent
    r = client.delete(f"/admin/agents/assign/{aa['id']}", headers=headers)
    assert r.status_code == 200

    # create agent role via convenience endpoint
    r = client.post('/admin/roles/make_agent', json={'user_id': agent.id}, headers=headers)
    assert r.status_code == 200
    # check role assigned
    r = client.get(f"/admin/users/{agent.id}/roles", headers=headers)
    assert r.status_code == 200
    roles = r.json()
    assert 'agent' in roles

    # remove agent role
    r = client.post('/admin/roles/remove_agent', json={'user_id': agent.id}, headers=headers)
    assert r.status_code == 200
    r = client.get(f"/admin/users/{agent.id}/roles", headers=headers)
    roles2 = r.json()
    assert 'agent' not in roles2
