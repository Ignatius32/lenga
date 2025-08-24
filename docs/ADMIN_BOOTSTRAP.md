# Admin bootstrap

This document describes how to create the first administrative user for the Quintral backend when you are running without Keycloak or when you need to bootstrap an initial admin.

Script: `scripts/create_first_admin.py`

Usage example:

```bash
python scripts/create_first_admin.py --keycloak-id admin-local --email admin@example.com --first-name Admin --last-name User
```

What the script does:
- Ensures DB tables exist (calls `Base.metadata.create_all`)
- Creates a `User` row with the provided keycloak_id/email/name if missing
- Creates a `Role` row named `admin` if missing
- Creates a `UserRole` linking the user to the `admin` role if missing

Notes:
- This script operates directly against the local DB configured in `app/core/database.py` / `app/core/config.py`.
- It is safe to re-run; it will not duplicate existing rows.
- For production use with Keycloak, you will typically assign realm roles in Keycloak; the script is intended for self-contained/demo setups.

After running the script you can call admin endpoints by authenticating as that user (in dev you can use `KEYCLOAK_BYPASS=True` and header `X-Test-User: <user_id>` to impersonate the admin).