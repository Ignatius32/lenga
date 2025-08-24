import pytest

from app.core.config import settings
from app.models import models


def test_ticket_history_shape(client, db_session):
    # enable bypass so x-test-user header works
    settings.KEYCLOAK_BYPASS = True

    # create a user who will create the ticket
    user = models.User(keycloak_id='u1', first_name='User', last_name='One', email='u1@example.com')
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # create a group and assign the user
    group = models.Group(name='G-test')
    db_session.add(group)
    db_session.commit()
    db_session.add(models.UserGroup(user_id=user.id, group_id=group.id))
    db_session.commit()

    # create a queue and give group's permission
    queue = models.Queue(name='Q-test')
    db_session.add(queue)
    db_session.commit()
    db_session.add(models.QueuePermission(group_id=group.id, queue_id=queue.id))
    db_session.commit()

    # create the ticket via API as the user (so permissions/flow are exercised)
    headers = {'x-test-user': str(user.id)}
    payload = {'subject': 'History test', 'description': 'Testing history shape', 'queue_id': queue.id}
    r = client.post('/tickets/', json=payload, headers=headers)
    if r.status_code != 200:
        print('POST /tickets/ returned', r.status_code)
        print('resp.text:', r.text)
    assert r.status_code == 200
    ticket = r.json()
    ticket_id = ticket['id']

    # create an actor user who will be the action_user/author/uploader
    actor = models.User(keycloak_id='actor1', first_name='Actor', last_name='User', email='actor@example.com')
    db_session.add(actor)
    db_session.commit()
    db_session.refresh(actor)

    # add a movement
    mv = models.TicketMovementLog(ticket_id=ticket_id, action_user_id=actor.id, action_type='TEST_ACTION', details='testing')
    db_session.add(mv)
    db_session.commit()

    # add a comment
    comment = models.TicketComment(ticket_id=ticket_id, author_user_id=actor.id, comment_text='a comment', is_internal=False)
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # add an attachment tied to the comment
    att = models.Attachment(ticket_id=ticket_id, comment_id=comment.id, file_name='f.txt', file_path='/tmp/f.txt', uploader_user_id=actor.id)
    db_session.add(att)
    db_session.commit()

    # request history as the ticket creator
    r = client.get(f'/tickets/{ticket_id}/history', headers=headers)
    assert r.status_code == 200
    body = r.json()

    # basic structure
    assert 'movements' in body and 'comments' in body and 'attachments' in body

    # movement includes nested action_user dict for the actor (may not be the first movement)
    assert isinstance(body['movements'], list)
    assert len(body['movements']) >= 1
    mov_found = [m for m in body['movements'] if m.get('action_user') and m['action_user'].get('id') == actor.id]
    assert len(mov_found) >= 1
    action_user = mov_found[0]['action_user']
    assert isinstance(action_user, dict)
    assert set(['id', 'keycloak_id', 'first_name', 'last_name', 'email']).issubset(set(action_user.keys()))

    # comment author nested (find the one authored by actor)
    assert isinstance(body['comments'], list)
    comment_found = [c for c in body['comments'] if c.get('author') and c['author'].get('id') == actor.id]
    assert len(comment_found) >= 1
    author = comment_found[0]['author']
    assert isinstance(author, dict)
    assert author['id'] == actor.id

    # attachment uploader nested (find uploader matching actor)
    assert isinstance(body['attachments'], list)
    att_found = [a for a in body['attachments'] if a.get('uploader') and a['uploader'].get('id') == actor.id]
    assert len(att_found) >= 1
    uploader = att_found[0]['uploader']
    assert isinstance(uploader, dict)
    assert uploader['keycloak_id'] == 'actor1'
