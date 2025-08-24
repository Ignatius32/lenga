import json
from app import models


def test_activity_type_and_activity_create(client, db_session):
    # ensure an admin user exists and use its id for admin endpoints
    from app import models as _models
    admin = db_session.query(_models.User).filter(_models.User.keycloak_id == 'test-admin').first()
    if not admin:
        admin = _models.User(keycloak_id='test-admin', first_name='Admin', last_name='User', email='admin@example.com')
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    role = db_session.query(_models.Role).filter(_models.Role.name == 'admin').first()
    if not role:
        role = _models.Role(name='admin')
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
    # assign role
    ur = db_session.query(_models.UserRole).filter(_models.UserRole.user_id == admin.id, _models.UserRole.role_id == role.id).first()
    if not ur:
        db_session.add(_models.UserRole(user_id=admin.id, role_id=role.id))
        db_session.commit()

    headers = {'x-test-user': str(admin.id)}

    # create a category
    r = client.post('/activities/categories', json={'name': 'Cat1'}, headers=headers)
    assert r.status_code == 200
    cat = r.json()

    # create a building and a space to reference
    r = client.post('/logistics/buildings', json={'name': 'B1', 'address': 'Addr'}, headers=headers)
    assert r.status_code == 200
    b = r.json()
    r = client.post('/logistics/spaces', json={'building_id': b['id'], 'name': 'S1', 'type': 'room', 'capacity': 10}, headers=headers)
    assert r.status_code == 200
    s = r.json()

    # create activity type with varied fields
    atype = {
        'name': 'AT1',
        'metadata': 'm',
        'fields': [
            {'name': 'note', 'field_type': 'text'},
            {'name': 'flag', 'field_type': 'boolean'},
            {'name': 'count', 'field_type': 'number'},
            {'name': 'when_dt', 'field_type': 'datetime'},
            {'name': 'when_d', 'field_type': 'date'},
            {'name': 'when_t', 'field_type': 'time'},
            {'name': 'room', 'field_type': 'space'},
            {'name': 'kind', 'field_type': 'select', 'options': ['X', 'Y']}
        ]
    }
    r = client.post('/activities/types', json=atype, headers=headers)
    assert r.status_code == 200
    t = r.json()

    # create activity using the template
    payload = {
        'title': 'Ev',
        'category_id': cat['id'],
        'start_time': '2025-08-25T09:00:00',
        'end_time': '2025-08-25T11:00:00',
        'organizer_user_id': 1,
        'activity_type_id': t['id'],
        'custom_fields': [
            {'name': 'note', 'value': 'hello'},
            {'name': 'flag', 'value': True},
            {'name': 'count', 'value': 12},
            {'name': 'when_dt', 'value': '2025-08-25T09:30:00'},
            {'name': 'when_d', 'value': '2025-08-25'},
            {'name': 'when_t', 'value': '09:30:00'},
            {'name': 'room', 'value': str(s['id'])},
            {'name': 'kind', 'value': 'Y'}
        ]
    }
    r = client.post('/activities/', json=payload, headers=headers)
    assert r.status_code == 200
    a = r.json()

    # check activity field values persisted
    vals = db_session.query(models.ActivityFieldValue).filter(models.ActivityFieldValue.activity_id == a['id']).all()
    assert len(vals) == 8
    # map by field_id
    by_field = {v.field_id: v.value for v in vals}
    # resolve field defs
    fdefs = db_session.query(models.ActivityTypeField).filter(models.ActivityTypeField.activity_type_id == t['id']).all()
    name_by_id = {f.id: f.name for f in fdefs}
    values_by_name = {name_by_id[k]: v for k, v in by_field.items()}
    assert values_by_name['note'] == 'hello'
    assert values_by_name['flag'] in ('true', 'false')
    assert values_by_name['count'] == '12'
    assert values_by_name['when_dt'].startswith('2025-08-25T09:30')
    assert values_by_name['when_d'] == '2025-08-25'
    assert values_by_name['when_t'].startswith('09:30')
    assert values_by_name['room'] == str(s['id'])
    assert values_by_name['kind'] == 'Y'
