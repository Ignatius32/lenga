import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models.models import Activity, ActivityCategory, Space, SpaceBooking
from datetime import datetime, timedelta

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    cat = ActivityCategory(name='Class')
    space = Space(name='Room 1', type='Classroom', capacity=30)
    db.add(cat)
    db.add(space)
    db.commit()
    db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def test_booking_conflict():
    db = SessionLocal()
    cat = db.query(ActivityCategory).first()
    space = db.query(Space).first()
    start = datetime.utcnow()
    end = start + timedelta(hours=1)
    a1 = Activity(title='A1', category_id=cat.id, start_time=start, end_time=end, organizer_user_id=1)
    db.add(a1)
    db.commit()
    db.refresh(a1)
    # confirm booking
    b1 = SpaceBooking(activity_id=a1.id, space_id=space.id, status='Confirmed')
    db.add(b1)
    db.commit()

    # create overlapping activity
    a2 = Activity(title='A2', category_id=cat.id, start_time=start + timedelta(minutes=30), end_time=end + timedelta(minutes=30), organizer_user_id=1)
    db.add(a2)
    db.commit()
    db.refresh(a2)
    # attempt to book same space should cause conflict via API
    r = client.post(f'/activities/{a2.id}/space_bookings', params={'space_id': space.id})
    assert r.status_code == 409
    db.close()
