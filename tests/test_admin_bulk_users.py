import io
from app.core.config import settings
from app.models import models


def test_bulk_create_users_endpoint(client, db_session):
    settings.KEYCLOAK_BYPASS = True
    # setup admin
    admin = models.User(keycloak_id='adm-bulk', first_name='AdminB', email='adm-bulk@example.com')
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    role = models.Role(name='admin')
    db_session.add(role)
    db_session.commit()
    db_session.add(models.UserRole(user_id=admin.id, role_id=role.id))
    db_session.commit()

    csv_content = 'keycloak_id,email,first_name,last_name,dni,roles\n'
    csv_content += 'u1,u1@example.com,User,One,123,agent;activity-manager\n'
    csv_content += 'u2,u2@example.com,User,Two,456,\n'

    headers = {'x-test-user': str(admin.id)}
    files = {'file': ('users.csv', csv_content)}
    r = client.post('/admin/users/bulk', files=files, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert 'results' in body
    assert body['results'][0]['status'] == 'created'
    assert body['results'][1]['status'] == 'created'

    # verify roles were created and assigned
    u1 = db_session.query(models.User).filter(models.User.keycloak_id == 'u1').first()
    assert u1 is not None
    roles = db_session.query(models.Role.name).join(models.UserRole, models.Role.id == models.UserRole.role_id).filter(models.UserRole.user_id == u1.id).all()
    names = [r[0] for r in roles]
    assert 'agent' in names and 'activity-manager' in names
