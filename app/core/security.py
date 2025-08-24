from typing import List, Optional
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt
import requests
import time
import logging

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.models import User
from sqlalchemy.orm import Session
logger = logging.getLogger(__name__)
security = HTTPBearer()


class AuthenticatedUser(BaseModel):
    id: int
    keycloak_id: str
    roles: List[str] = []


# JWKS cache
_JWKS_CACHE = {"keys": None, "fetched_at": 0, "ttl": 3600}


def _get_jwks():
    """Fetch JWKS from Keycloak and cache for TTL seconds."""
    now = time.time()
    if _JWKS_CACHE['keys'] and (now - _JWKS_CACHE['fetched_at'] < _JWKS_CACHE['ttl']):
        return _JWKS_CACHE['keys']
    jwks_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        r = requests.get(jwks_url, timeout=5)
        r.raise_for_status()
        jwks = r.json()
        _JWKS_CACHE['keys'] = jwks
        _JWKS_CACHE['fetched_at'] = now
        return jwks
    except Exception as e:
        logger.exception('Failed to fetch JWKS')
        raise HTTPException(status_code=502, detail='Failed to fetch JWKS')


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False))) -> AuthenticatedUser:
    # If bypass mode is enabled, prefer the bypass dependency in routes that use it.
    # This function will still be used as a fallback for routes that call it directly.
    if settings.KEYCLOAK_BYPASS:
        raise HTTPException(status_code=500, detail='KEYCLOAK_BYPASS requires using get_current_user_bypass in route')

    # If no credentials were provided, return an anonymous user (id=0, no roles).
    # This allows unauthenticated endpoints to function in tests and in public routes.
    if credentials is None:
        return AuthenticatedUser(id=0, keycloak_id='', roles=[])

    token = credentials.credentials
    # Get JWKS; in tests jwt.decode can be monkeypatched to bypass actual verification
    jwks = _get_jwks()
    try:
        # Allow jwt.decode to be mocked in tests; production will validate signature
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        key = None
        for k in jwks.get('keys', []):
            if k.get('kid') == kid:
                key = k
                break
        if not key:
            raise HTTPException(status_code=401, detail='Public key not found')

        public_key = jwt.construct_rsa_key(key)
        issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[unverified_header.get('alg', 'RS256')],
            audience=settings.KEYCLOAK_CLIENT_ID,
            issuer=issuer,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('Token validation failed')
        raise HTTPException(status_code=401, detail='Invalid token')

    sub = claims.get('sub')
    if not sub:
        raise HTTPException(status_code=401, detail='Invalid token: missing sub')

    roles = []
    realm_access = claims.get('realm_access')
    if realm_access and isinstance(realm_access, dict):
        roles = realm_access.get('roles', []) or []

    # Ensure local user exists (cache basic profile)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.keycloak_id == sub).first()
        if not user:
            user = User(
                keycloak_id=sub,
                email=claims.get('email'),
                first_name=claims.get('given_name'),
                last_name=claims.get('family_name'),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    return AuthenticatedUser(id=user.id, keycloak_id=sub, roles=roles)


def require_role(required_role: str):
    def _dependency(user: AuthenticatedUser = Depends(get_current_user_bypass)):
        if required_role not in user.roles:
            raise HTTPException(status_code=403, detail='Missing required role')
        return True

    return _dependency


def get_current_user_bypass(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False)), db: Session = Depends(get_db)) -> AuthenticatedUser:
    """Alternate dependency to use when KEYCLOAK_BYPASS is enabled in settings.
    This will accept a header X-Test-User with a numeric user id to impersonate that user.
    If an Authorization bearer token is present it tries to fallback to normal behaviour.

    Important: do NOT close the `db` session provided by DI here. The session may be
    controlled by the caller (tests override get_db) and closing it would detach instances
    and interfere with test fixtures.
    """
    if not settings.KEYCLOAK_BYPASS:
        # fall back to normal behavior
        return get_current_user(credentials)

    # Try X-Test-User header
    test_user_header = request.headers.get('x-test-user')
    # Use provided db session (this allows tests to override get_db)
    if test_user_header:
        try:
            uid = int(test_user_header)
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid X-Test-User header')
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            # In dev bypass mode, auto-create a minimal test user when the requested id
            # does not exist. This allows the admin SPA to continue working after the
            # local test DB was reset without requiring manual user creation.
            try:
                user = User(id=uid, keycloak_id=f'dev-{uid}', first_name='Dev', last_name=str(uid), email=None)
                db.add(user)
                db.flush()
                # ensure an 'admin' role exists and assign it to the test user so
                # admin-only endpoints are accessible in dev mode after DB reset
                from app.models.models import Role, UserRole
                role = db.query(Role).filter(Role.name == 'admin').first()
                if not role:
                    role = Role(name='admin')
                    db.add(role)
                    db.flush()
                # create user role mapping if missing
                ur = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
                if not ur:
                    ur = UserRole(user_id=user.id, role_id=role.id)
                    db.add(ur)
                db.commit()
                db.refresh(user)
            except Exception:
                # fallback: surface a clear 404 if we cannot create the user for any reason
                raise HTTPException(status_code=404, detail='Test user not found and could not be created')
        logger.debug("get_current_user_bypass: header x-test-user=%s", test_user_header)
        logger.info("get_current_user_bypass: impersonating test user id=%s", uid)
        # gather roles from UserRole -> Role
        from app.models.models import UserRole, Role
        role_rows = db.query(Role.name).join(UserRole, Role.id == UserRole.role_id).filter(UserRole.user_id == user.id).all()
        roles = [r[0] for r in role_rows]
        logger.debug("get_current_user_bypass: resolved roles=%s for user id=%s", roles, uid)
        logger.info("get_current_user_bypass: resolved roles=%s for user id=%s", roles, uid)
        return AuthenticatedUser(id=user.id, keycloak_id=user.keycloak_id, roles=roles)

    # else fallback to token path
    # If no credentials were provided (e.g., anonymous request in tests), return an anonymous user
    # with no roles so endpoints that don't require authentication can proceed.
    if credentials is None:
        return AuthenticatedUser(id=0, keycloak_id='', roles=[])
    return get_current_user(credentials)
