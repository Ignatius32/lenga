from datetime import datetime

from app.models import models
from app.core.config import settings


def create_user(session, keycloak_id='u-1', email='u@example.com', first_name=None, last_name=None):
    u = session.query(models.User).filter(models.User.keycloak_id == keycloak_id).first()
    if u:
        return u
    u = models.User(keycloak_id=keycloak_id, email=email, first_name=first_name, last_name=last_name)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_integral_helpdesk_flow(client, db_session):
    """End-to-end helpdesk flow:
    - ensure admin, client and agent exist
    - admin creates queue and ticket type
    - admin grants client's group permission for queue
    - client creates a ticket of that type in the queue
    - admin assigns agent to queue
    - agent can access ticket history
    - client can view own ticket
    """
    settings.KEYCLOAK_BYPASS = True

    # create or get users
    admin = create_user(db_session, keycloak_id='admin-int', email='admin-int@example.com')
    client_user = create_user(db_session, keycloak_id='client-int', email='client-int@example.com')
    agent = create_user(db_session, keycloak_id='agent-int', email='agent-int@example.com')

    # ensure admin role exists and assign
    role_admin = db_session.query(models.Role).filter(models.Role.name == 'admin').first()
    if not role_admin:
        role_admin = models.Role(name='admin')
        db_session.add(role_admin)
        db_session.commit()
    ur = db_session.query(models.UserRole).filter(models.UserRole.user_id == admin.id, models.UserRole.role_id == role_admin.id).first()
    if not ur:
        db_session.add(models.UserRole(user_id=admin.id, role_id=role_admin.id))
        db_session.commit()

    headers_admin = {'x-test-user': str(admin.id)}

    # create a clients group and add client_user to it
    grp = db_session.query(models.Group).filter(models.Group.name == 'Clients').first()
    if not grp:
        grp = models.Group(name='Clients')
        db_session.add(grp)
        db_session.commit()
    ug = db_session.query(models.UserGroup).filter(models.UserGroup.user_id == client_user.id, models.UserGroup.group_id == grp.id).first()
    if not ug:
        db_session.add(models.UserGroup(user_id=client_user.id, group_id=grp.id))
        db_session.commit()

    # admin creates a queue
    r = client.post('/admin/queues', json={'name': 'Helpdesk', 'description': 'Helpdesk queue'}, headers=headers_admin)
    assert r.status_code == 200
    q = r.json()

    # admin grants group's permission to post in queue
    r = client.post('/admin/queue_permissions', json={'group_id': grp.id, 'queue_id': q['id']}, headers=headers_admin)
    assert r.status_code == 200

    # admin creates a ticket type attached to the queue and allowed for the Clients group
    payload = {'queue_id': q['id'], 'name': 'General Inquiry', 'allowed_group_ids': [grp.id], 'fields': []}
    r = client.post('/admin/ticket_types', json=payload, headers=headers_admin)
    assert r.status_code == 200
    tt = r.json()

    # client creates a ticket in that queue
    headers_client = {'x-test-user': str(client_user.id)}
    ticket_payload = {'subject': 'Need help', 'description': 'My issue', 'queue_id': q['id'], 'ticket_type_id': tt['id']}
    r = client.post('/tickets/', json=ticket_payload, headers=headers_client)
    assert r.status_code == 200
    ticket = r.json()
    assert ticket['client_user_id'] == client_user.id

    # admin assigns agent to the queue
    r = client.post('/admin/agents/assign', json={'agent_user_id': agent.id, 'queue_id': q['id'], 'access_level': 'full'}, headers=headers_admin)
    assert r.status_code == 200
    aa = r.json()

    # agent should be able to view ticket history
    headers_agent = {'x-test-user': str(agent.id)}
    r = client.get(f"/tickets/{ticket['id']}/history", headers=headers_agent)
    assert r.status_code == 200
    hist = r.json()
    assert hist['ticket_id'] == ticket['id']

    # client can view their ticket
    r = client.get(f"/tickets/{ticket['id']}", headers=headers_client)
    assert r.status_code == 200
    t2 = r.json()
    assert t2['id'] == ticket['id']

    # cleanup: unassign agent
    r = client.delete(f"/admin/agents/assign/{aa['id']}", headers=headers_admin)
    assert r.status_code == 200
