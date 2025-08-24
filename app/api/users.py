from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_bypass
from app import models, schemas

router = APIRouter(tags=["users"])


@router.get('/me', response_model=schemas.UserProfileOut)
def me(user=Depends(get_current_user_bypass), db: Session = Depends(get_db)):
    # user is AuthenticatedUser (pydantic model) with id/keycloak_id/roles
    if user.id == 0:
        return schemas.UserProfileOut(id=0, keycloak_id='', first_name=None, last_name=None, email=None, roles=[], groups=[])
    # load groups
    grows = db.query(models.UserGroup).filter(models.UserGroup.user_id == user.id).all()
    group_ids = [g.group_id for g in grows]
    # load local user record
    u = db.query(models.User).filter(models.User.id == user.id).first()
    return schemas.UserProfileOut(id=u.id, keycloak_id=u.keycloak_id, first_name=u.first_name, last_name=u.last_name, email=u.email, roles=user.roles, groups=group_ids)
