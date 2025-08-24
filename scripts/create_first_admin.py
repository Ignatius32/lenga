"""Small script to create the first admin user in the local DB and assign the 'admin' role.

Usage:
  python scripts/create_first_admin.py --keycloak-id <kc-id> --email <email> --first-name <first> --last-name <last>

This script uses the same DB configuration as the app and creates a user and assigns the 'admin' role.
"""
import argparse
from app.core.database import SessionLocal, Base, engine
from app import models


def create_admin(keycloak_id, email, first_name, last_name, dni=None):
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        # create user if missing
        u = db.query(models.User).filter(models.User.keycloak_id == keycloak_id).first()
        if not u:
            u = models.User(keycloak_id=keycloak_id, email=email, first_name=first_name, last_name=last_name, dni=dni)
            db.add(u)
            db.commit()
            db.refresh(u)
            print(f"Created user id={u.id}")
        else:
            print(f"User already exists id={u.id}")
        # ensure role exists
        r = db.query(models.Role).filter(models.Role.name == 'admin').first()
        if not r:
            r = models.Role(name='admin')
            db.add(r)
            db.commit()
            db.refresh(r)
            print('Created role admin')
        # assign role if not assigned
        ur = db.query(models.UserRole).filter(models.UserRole.user_id == u.id, models.UserRole.role_id == r.id).first()
        if not ur:
            ur = models.UserRole(user_id=u.id, role_id=r.id)
            db.add(ur)
            db.commit()
            print('Assigned admin role to user')
        else:
            print('User already has admin role')
    finally:
        db.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--keycloak-id', required=True)
    p.add_argument('--email', required=True)
    p.add_argument('--first-name', required=True)
    p.add_argument('--last-name', required=True)
    p.add_argument('--dni', required=False)
    args = p.parse_args()
    create_admin(args.keycloak_id, args.email, args.first_name, args.last_name, args.dni)
