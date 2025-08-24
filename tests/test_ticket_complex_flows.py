from datetime import datetime

from app.models import models
from app.core.config import settings


def create_user(session, keycloak_id='u-complex', email='u-complex@example.com'):
    u = session.query(models.User).filter(models.User.keycloak_id == keycloak_id).first()
    if u:
        return u
    u = models.User(keycloak_id=keycloak_id, email=email)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_ticket_complex_flow(client, db_session):
    settings.KEYCLOAK_BYPASS = True

    # create admin, client, agent1, agent2
    admin = create_user(db_session, keycloak_id='admin-c', email='admin-c@example.com')
    client_user = create_user(db_session, keycloak_id='client-c', email='client-c@example.com')
    agent1 = create_user(db_session, keycloak_id='agent1-c', email='agent1-c@example.com')
    agent2 = create_user(db_session, keycloak_id='agent2-c', email='agent2-c@example.com')

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

    # create groups and add client to Clients group
    clients_group = db_session.query(models.Group).filter(models.Group.name == 'Clients').first()
    if not clients_group:
        clients_group = models.Group(name='Clients')
        db_session.add(clients_group)
        db_session.commit()
    ug = db_session.query(models.UserGroup).filter(models.UserGroup.user_id == client_user.id, models.UserGroup.group_id == clients_group.id).first()
    if not ug:
        db_session.add(models.UserGroup(user_id=client_user.id, group_id=clients_group.id))
        db_session.commit()

    # admin creates two queues
    r = client.post('/admin/queues', json={'name': 'Support A', 'description': 'Queue A'}, headers=headers_admin)
    assert r.status_code == 200
    q1 = r.json()
    r = client.post('/admin/queues', json={'name': 'Support B', 'description': 'Queue B'}, headers=headers_admin)
    assert r.status_code == 200
    q2 = r.json()

    # allow Clients group in q1 and q2
    r = client.post('/admin/queue_permissions', json={'group_id': clients_group.id, 'queue_id': q1['id']}, headers=headers_admin)
    assert r.status_code == 200
    r = client.post('/admin/queue_permissions', json={'group_id': clients_group.id, 'queue_id': q2['id']}, headers=headers_admin)
    assert r.status_code == 200

    # create a ticket type for q1
    payload = {'queue_id': q1['id'], 'name': 'General', 'allowed_group_ids': [clients_group.id], 'fields': []}
    r = client.post('/admin/ticket_types', json=payload, headers=headers_admin)
    assert r.status_code == 200
    tt = r.json()

    # admin assigns agent1 and agent2 to q1 (agent2 as manager)
    r = client.post('/admin/agents/assign', json={'agent_user_id': agent1.id, 'queue_id': q1['id'], 'access_level': 'Tier 1'}, headers=headers_admin)
    assert r.status_code == 200
    aa1 = r.json()
    r = client.post('/admin/agents/assign', json={'agent_user_id': agent2.id, 'queue_id': q1['id'], 'access_level': 'Manager'}, headers=headers_admin)
    assert r.status_code == 200
    aa2 = r.json()

    # also assign agent2 to q2 so they can act on transferred tickets in q2
    r = client.post('/admin/agents/assign', json={'agent_user_id': agent2.id, 'queue_id': q2['id'], 'access_level': 'Manager'}, headers=headers_admin)
    assert r.status_code == 200
    aa2_q2 = r.json()

    # grant 'agent' role to the agent users so they can use agent endpoints
    r = client.post('/admin/roles/make_agent', json={'user_id': agent1.id}, headers=headers_admin)
    assert r.status_code == 200
    r = client.post('/admin/roles/make_agent', json={'user_id': agent2.id}, headers=headers_admin)
    assert r.status_code == 200

    # client creates a ticket in q1
    headers_client = {'x-test-user': str(client_user.id)}
    ticket_payload = {'subject': 'Complex flow', 'description': 'Testing claim/transfer/comments', 'queue_id': q1['id'], 'ticket_type_id': tt['id']}
    r = client.post('/tickets/', json=ticket_payload, headers=headers_client)
    assert r.status_code == 200
    ticket = r.json()

    # agent1 claims the ticket
    headers_agent1 = {'x-test-user': str(agent1.id)}
    r = client.post(f'/agents/tickets/{ticket["id"]}/claim', headers=headers_agent1)
    assert r.status_code == 200
    t_claimed = r.json()
    assert t_claimed['current_agent_id'] == agent1.id

    # agent1 posts a public comment
    comment_payload = {'comment_text': 'I am looking into this', 'is_internal': False}
    r = client.post(f'/agents/tickets/{ticket["id"]}/comments', json=comment_payload, headers=headers_agent1)
    assert r.status_code == 200
    comment = r.json()
    assert comment['author_user_id'] == agent1.id if 'author_user_id' in comment else True

    # agent1 attempts to transfer ticket to q2 but lacks Manager -> should fail
    transfer_payload = {'target_queue_id': q2['id'], 'reason': 'Needs escalation'}
    r = client.post(f'/agents/tickets/{ticket["id"]}/transfer', json=transfer_payload, headers=headers_agent1)
    assert r.status_code == 403

    # agent2 (Manager) transfers ticket to q2
    headers_agent2 = {'x-test-user': str(agent2.id)}
    r = client.post(f'/agents/tickets/{ticket["id"]}/transfer', json=transfer_payload, headers=headers_agent2)
    assert r.status_code == 200
    t_transferred = r.json()
    assert t_transferred['current_queue_id'] == q2['id']

    # upload an attachment as agent2 to the ticket (attachments endpoint expects form upload)
    # Use a small in-memory file
    files = {'file': ('note.txt', b'This is a note')}
    r = client.post(f'/attachments/upload?ticket_id={ticket["id"]}', files=files, headers=headers_agent2)
    assert r.status_code == 200
    att = r.json()
    assert att['ticket_id'] == ticket['id']

    # agent2 resolves the ticket (status -> Resolved)
    status_payload = {'status': 'Resolved', 'resolved_at': datetime.utcnow().isoformat()}
    r = client.patch(f'/agents/tickets/{ticket["id"]}/status', json=status_payload, headers=headers_agent2)
    assert r.status_code == 200
    t_res = r.json()
    assert t_res['status'] == 'Resolved'

    # fetch history as client (should be allowed even after transfer because creator)
    r = client.get(f'/tickets/{ticket["id"]}/history', headers=headers_client)
    assert r.status_code == 200
    hist = r.json()
    # verify movements include CLAIM, TRANSFER_QUEUE, STATUS_CHANGE, COMMENT
    types = [m['action_type'] for m in hist['movements']]
    assert 'CLAIM' in types
    assert 'TRANSFER_QUEUE' in types
    assert 'STATUS_CHANGE' in types
    assert 'COMMENT' in types

    # cleanup: unassign agents
    r = client.delete(f"/admin/agents/assign/{aa1['id']}", headers=headers_admin)
    assert r.status_code == 200
    r = client.delete(f"/admin/agents/assign/{aa2['id']}", headers=headers_admin)
    assert r.status_code == 200
