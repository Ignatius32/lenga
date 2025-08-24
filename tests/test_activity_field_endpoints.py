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


def test_activity_field_crud_and_value_cleanup(client, db_session):
    settings.KEYCLOAK_BYPASS = True

    admin = create_user(db_session, keycloak_id='admin-kc2', email='admin2@example.com')
    org = create_user(db_session, keycloak_id='org-kc2', email='org2@example.com')

    # give admin the admin role
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    headers = {'x-test-user': str(admin.id)}

    # create a base activity type
    r = client.post('/activities/types', json={'name': 'Seminar', 'metadata': '{}'}, headers=headers)
    assert r.status_code == 200
    at = r.json()

    # add a select field
    r = client.post(f"/activities/types/{at['id']}/fields", json={'name': 'Difficulty', 'field_type': 'select', 'options': ['A','B']}, headers=headers)
    assert r.status_code == 200
    f = r.json()
    assert f['field_type'] == 'select'

    # add a text field
    r = client.post(f"/activities/types/{at['id']}/fields", json={'name': 'Notes', 'field_type': 'text'}, headers=headers)
    assert r.status_code == 200
    f2 = r.json()

    # create activity referencing these fields
    a_start = datetime.utcnow() + timedelta(hours=1)
    a_end = a_start + timedelta(hours=2)
    headers_org = {'x-test-user': str(org.id)}
    payload2 = {
        'title': 'Seminar 1',
        'category_id': 1,
        'activity_type_id': at['id'],
        'start_time': a_start.isoformat(),
        'end_time': a_end.isoformat(),
        'organizer_user_id': org.id,
        'custom_fields': [
            {'field_id': f['id'], 'value': 'A'},
            {'field_id': f2['id'], 'value': 'Some notes'}
        ]
    }
    r = client.post('/activities/', json=payload2, headers=headers_org)
    assert r.status_code == 200
    a = r.json()

    # ensure values persisted
    vals = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals) == 2

    # update select options to remove 'A' -> values with 'A' should be deleted
    r = client.patch(f"/activities/types/{at['id']}/fields/{f['id']}", json={'options': ['C']}, headers=headers)
    assert r.status_code == 200
    # values should be pruned
    vals2 = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals2) == 1

    # change field type of text field to select -> that will remove existing values for that field
    r = client.patch(f"/activities/types/{at['id']}/fields/{f2['id']}", json={'field_type': 'select', 'options': ['X']}, headers=headers)
    assert r.status_code == 200
    # any values for that field should be removed
    vals3 = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals3) == 0

    # recreate a field and then delete it
    r = client.post(f"/activities/types/{at['id']}/fields", json={'name': 'Tmp', 'field_type': 'text'}, headers=headers)
    assert r.status_code == 200
    tmp = r.json()
    # add a value for this field
    db_session.add(models.ActivityFieldValue(activity_id=a['id'], field_id=tmp['id'], value='v'))
    db_session.commit()
    vals4 = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals4) == 1
    # delete field -> values removed
    r = client.delete(f"/activities/types/{at['id']}/fields/{tmp['id']}", headers=headers)
    assert r.status_code in (200, 204)
    vals5 = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals5) == 0
