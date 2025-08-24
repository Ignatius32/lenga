import json
from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.models import models


def create_user(session, keycloak_id='test-kc-1', first_name='Test', last_name='User', email='u@example.com'):
    u = models.User(keycloak_id=keycloak_id, first_name=first_name, last_name=last_name, email=email)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_activity_templates_and_custom_fields(client, db_session):
    settings.KEYCLOAK_BYPASS = True

    admin = create_user(db_session, keycloak_id='admin-kc', email='admin@example.com')
    org = create_user(db_session, keycloak_id='org-kc', email='org@example.com')

    # give admin the admin role
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    headers = {'x-test-user': str(admin.id)}

    # create activity type with a select and space field
    payload = {
        'name': 'Workshop',
        'metadata': '{}',
        'fields': [
            {'name': 'Level', 'field_type': 'select', 'options': ['Beginner', 'Intermediate', 'Advanced']},
            {'name': 'Room', 'field_type': 'space'}
        ]
    }
    r = client.post('/activities/types', json=payload, headers=headers)
    assert r.status_code == 200
    at = r.json()
    assert 'fields' in at and len(at['fields']) == 2

    # create a building and space to reference
    b = models.Building(name='B')
    db_session.add(b)
    db_session.commit()
    sp = models.Space(building_id=b.id, name='Main')
    db_session.add(sp)
    db_session.commit()

    # create activity using template with valid select and space
    a_start = datetime.utcnow() + timedelta(hours=1)
    a_end = a_start + timedelta(hours=2)
    headers_org = {'x-test-user': str(org.id)}
    custom_fields = [
        {'field_id': at['fields'][0]['id'], 'value': 'Intermediate'},
        {'field_id': at['fields'][1]['id'], 'value': str(sp.id)}
    ]
    payload2 = {
        'title': 'Workshop Session',
        'category_id': 1,
        'activity_type_id': at['id'],
        'start_time': a_start.isoformat(),
        'end_time': a_end.isoformat(),
        'organizer_user_id': org.id,
        'custom_fields': custom_fields
    }
    r = client.post('/activities/', json=payload2, headers=headers_org)
    assert r.status_code == 200
    a = r.json()
    # ensure custom fields present in response
    assert 'custom_fields' in a
    # check DB persisted values
    vals = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals) == 2

    # now attempt to create with invalid select option
    payload3 = payload2.copy()
    payload3['title'] = 'Bad Option'
    payload3['custom_fields'] = [
        {'field_id': at['fields'][0]['id'], 'value': 'NotARealChoice'},
        {'field_id': at['fields'][1]['id'], 'value': str(sp.id)}
    ]
    r = client.post('/activities/', json=payload3, headers=headers_org)
    assert r.status_code == 400

    # attempt to create with invalid space id
    payload4 = payload2.copy()
    payload4['title'] = 'Bad Space'
    payload4['custom_fields'] = [
        {'field_id': at['fields'][0]['id'], 'value': 'Beginner'},
        {'field_id': at['fields'][1]['id'], 'value': '99999'}
    ]
    r = client.post('/activities/', json=payload4, headers=headers_org)
    assert r.status_code == 400
