import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {'Content-Type': 'application/json', 'x-test-user': '1'}


def make_building():
    r = client.post('/logistics/buildings', headers=HEADERS, json={'name': 'OvBld', 'address': 'Test address'})
    if r.status_code not in (200, 201):
        # surface response for debugging
        print('BUILDING CREATE FAILED', r.status_code, r.text)
    assert r.status_code in (200, 201)
    return r.json()


def make_space(building_id, template_id=None):
    payload = {'building_id': building_id, 'name': 'Room1', 'type': 'room', 'capacity': 10}
    if template_id:
        payload['space_template_id'] = template_id
    r = client.post('/logistics/spaces', headers=HEADERS, json=payload)
    assert r.status_code in (200, 201)
    return r.json()


def make_activity_type():
    # activity type with a space field and simple datetime fields
    payload = {
        'name': 'OverlapType',
        'fields': [
            {'name': 'room', 'field_type': 'space'},
            {'name': 'is_virtual', 'field_type': 'boolean'}
        ]
    }
    r = client.post('/activities/types', headers=HEADERS, json=payload)
    assert r.status_code in (200, 201)
    return r.json()


def create_activity(payload, expect_success=True):
    r = client.post('/activities/', headers=HEADERS, json=payload)
    if expect_success:
        assert r.status_code == 200, f"Expected success, got {r.status_code} {r.text}"
        return r.json()
    else:
        assert r.status_code >= 400, f"Expected failure, got {r.status_code} {r.text}"
        return r


def test_activity_overlap_flow():
    # create building & space
    b = make_building()
    s = make_space(b['id'])

    # create activity type
    at = make_activity_type()

    # create first activity occupying 9:00-10:00 on 2025-08-26
    payload1 = {
        'title': 'First',
        'category_id': 1,
        'start_time': '2025-08-26T09:00:00',
        'end_time': '2025-08-26T10:00:00',
        'organizer_user_id': 1,
        'activity_type_id': at['id'],
        'custom_fields': [
            {'name': 'room', 'value': str(s['id'])},
            {'name': 'is_virtual', 'value': False}
        ]
    }
    a1 = create_activity(payload1, expect_success=True)
    # book the first activity (confirm booking)
    rbook1 = client.post(f"/activities/{a1['id']}/space_bookings", headers=HEADERS, json={'space_id': s['id'], 'status': 'Confirmed'})
    assert rbook1.status_code == 200, f"Booking first activity failed: {rbook1.status_code} {rbook1.text}"

    # attempt overlapping activity 9:30-10:30 same room -> booking should fail
    payload2 = {
        'title': 'Overlap',
        'category_id': 1,
        'start_time': '2025-08-26T09:30:00',
        'end_time': '2025-08-26T10:30:00',
        'organizer_user_id': 1,
        'activity_type_id': at['id'],
        'custom_fields': [
            {'name': 'room', 'value': str(s['id'])},
            {'name': 'is_virtual', 'value': False}
        ]
    }
    a2 = create_activity(payload2, expect_success=True)
    # attempt to book the overlapping activity - should get 409 Conflict
    rbook2 = client.post(f"/activities/{a2['id']}/space_bookings", headers=HEADERS, json={'space_id': s['id'], 'status': 'Confirmed'})
    assert rbook2.status_code == 409, f"Expected booking conflict (409), got {rbook2.status_code} {rbook2.text}"

    # attempt non-overlapping activity 10:00-11:00 same room -> should be allowed
    payload3 = {
        'title': 'After',
        'category_id': 1,
        'start_time': '2025-08-26T10:00:00',
        'end_time': '2025-08-26T11:00:00',
        'organizer_user_id': 1,
        'activity_type_id': at['id'],
        'custom_fields': [
            {'name': 'room', 'value': str(s['id'])},
            {'name': 'is_virtual', 'value': False}
        ]
    }
    # We'll accept either success (200) or failure depending on exact server overlap policy; assert success is preferable
    a3 = create_activity(payload3, expect_success=True)
    rbook3 = client.post(f"/activities/{a3['id']}/space_bookings", headers=HEADERS, json={'space_id': s['id'], 'status': 'Confirmed'})
    assert rbook3.status_code == 200, f"Expected booking success for non-overlap, got {rbook3.status_code} {rbook3.text}"
