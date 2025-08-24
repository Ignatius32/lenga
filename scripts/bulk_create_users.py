"""CLI helper to import users from a CSV file locally using the app database.

CSV expected headers: keycloak_id,email,first_name,last_name,dni,roles
Roles can be semicolon-separated values. This script mirrors the admin bulk endpoint.

Usage:
  .venv/bin/python3 scripts/bulk_create_users.py users.csv
"""
import sys
import csv
from app.core.database import SessionLocal, Base, engine
from app import models


def import_csv(path):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                kc = row.get('keycloak_id')
                if not kc:
                    print('skipping row missing keycloak_id')
                    continue
                u = db.query(models.User).filter(models.User.keycloak_id == kc).first()
                if not u:
                    u = models.User(keycloak_id=kc, email=row.get('email'), first_name=row.get('first_name'), last_name=row.get('last_name'), dni=row.get('dni'))
                    db.add(u)
                    db.flush()
                    print('created user', u.id)
                else:
                    if row.get('email'):
                        u.email = row.get('email')
                    if row.get('first_name'):
                        u.first_name = row.get('first_name')
                    if row.get('last_name'):
                        u.last_name = row.get('last_name')
                    if row.get('dni'):
                        u.dni = row.get('dni')
                    print('updated user', u.id)
                roles_cell = row.get('roles') or ''
                roles = [r.strip() for r in roles_cell.split(';') if r.strip()]
                for rn in roles:
                    role = db.query(models.Role).filter(models.Role.name == rn).first()
                    if not role:
                        role = models.Role(name=rn)
                        db.add(role)
                        db.flush()
                        print('created role', rn)
                    ur = db.query(models.UserRole).filter(models.UserRole.user_id == u.id, models.UserRole.role_id == role.id).first()
                    if not ur:
                        db.add(models.UserRole(user_id=u.id, role_id=role.id))
                db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: bulk_create_users.py users.csv')
        sys.exit(1)
    import_csv(sys.argv[1])
    print('done')
