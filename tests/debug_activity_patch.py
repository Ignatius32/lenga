from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app import models

TEST_DATABASE_URL = "sqlite:///./test_institution_manager.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# create tables
Base.metadata.create_all(bind=engine)

# start a session similar to test fixture
connection = engine.connect()
transaction = connection.begin()
session = TestingSessionLocal(bind=connection)

# override get_db
def override_get_db():
    try:
        yield session
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db
settings.KEYCLOAK_BYPASS = True
client = TestClient(app)

# create admin and org
admin = models.User(keycloak_id='admin-kc', email='admin@example.com')
session.add(admin)
org = models.User(keycloak_id='org-kc', email='org@example.com')
session.add(org)
session.commit()
session.refresh(admin)
session.refresh(org)

# assign admin role
role = models.Role(name='admin')
session.add(role)
session.commit()
session.add(models.UserRole(user_id=admin.id, role_id=role.id))
session.commit()

# create activity type as admin
headers = {'x-test-user': str(admin.id)}
r = client.post('/activities/types', params={'name': 'Lecture', 'metadata': '[]'}, headers=headers)
print('create type status', r.status_code, r.text)
at = r.json()

# create activity as organizer
from datetime import datetime, timedelta

start = datetime.utcnow() + timedelta(hours=1)
end = start + timedelta(hours=2)
headers_org = {'x-test-user': str(org.id)}
payload = {
    'title': 'Test Event',
    'category_id': 1,
    'activity_type_id': at['id'],
    'start_time': start.isoformat(),
    'end_time': end.isoformat(),
    'organizer_user_id': org.id
}
r = client.post('/activities/', json=payload, headers=headers_org)
print('create activity status', r.status_code, r.text)

# assign activity-manager to organizer so they can update/delete
role_am = models.Role(name='activity-manager')
session.add(role_am)
session.commit()
session.add(models.UserRole(user_id=org.id, role_id=role_am.id))
session.commit()

# attempt patch
new_start = start + timedelta(minutes=10)
new_end = end + timedelta(minutes=10)
r = client.patch(f"/activities/1", json={'start_time': new_start.isoformat(), 'end_time': new_end.isoformat()}, headers=headers_org)
print('patch status', r.status_code, r.text)

# cleanup
session.close()
transaction.rollback()
connection.close()

