# Keycloak realm "CRUB" configuration for Quintral Helpdesk & Logistics backend

This document describes a recommended Keycloak realm configuration named `CRUB` to integrate with the Quintral backend (FastAPI) in this repository. It focuses on the minimal clients, roles, mappers and sample user role assignments the backend expects.

Summary
- Realm name: `CRUB`
- Public client: `institution-client` (or confidential if you prefer server-side flows)
- Expected token claims: `sub`, `email`, `given_name`, `family_name`, and `realm_access.roles`
- Recommended realm-level roles: `admin`, `activity-manager`, plus any project-specific roles you want to use in the UI

Why this configuration
- The backend validates JWTs issued by Keycloak and expects user identity information (sub/email/first/last) and roles in `realm_access.roles` to power authorization checks such as admin-only endpoints.
- In development/test, the repo includes a `KEYCLOAK_BYPASS` test mode that skips Keycloak validation. For production, configure Keycloak properly and disable bypass.

Configuration steps

1) Create realm
- Create a new realm in Keycloak named `CRUB`.

2) Create realm roles
- Go to Roles -> Add Role and add at least the following realm-level roles:
  - `admin` — full administrative access; used by the backend to allow admin-only endpoints
  - `activity-manager` — used by activity endpoints in the codebase as an example of a role that allows updates/deletes for activities (and similar manager roles can be added for other resources)

  Optionally add:
  - `agent` — if you want to model agents separately; note that the backend also persists agent assignments in the DB (AgentAssignment) so you may not need a Keycloak role for agents unless you want Keycloak-driven UI restrictions.

3) Create a client
- Create a client with Client ID: `institution-client` (this matches the default in `app/core/config.py`).
- Choose Access Type:
  - `public` if you only use browser-based flows and don't need client secret.
  - `confidential` if your backend will perform direct token exchange or if you prefer a secret-based client for server-to-server flows.
- Valid Redirect URIs: configure as needed for your frontend apps (for development, you can use `http://localhost:3000/*`).
- Web Origins: set to `*` for development or limit to your frontend origin in production.

4) Client settings and mappers
- In the client settings, ensure `Client ID` matches `KEYCLOAK_CLIENT_ID` from `app/core/config.py` (default `institution-client`).
- Under the client `Mappers` tab, add mappers if needed to include attributes in access tokens. The backend expects:
  - `sub` is automatically present (subject)
  - `email` — add the built-in `email` mapper if not already present
  - `given_name` and `family_name` — built-in mappers supply these when users have first/last names set

  Roles mapping:
  - The default token includes realm roles under `realm_access.roles`. If you've set `Include in token` for client roles, they will appear under `resource_access.<client-id>.roles` instead. The backend currently reads `realm_access.roles` — prefer realm-level roles or adjust backend code to read client roles.

5) Create test users and assign roles
- Users -> Add user
  - Create at least one admin user and one regular user.
  - For each user, in the `Credentials` tab set a password (temporary) and enable the account.
  - For the admin user, assign the `admin` role in `Role Mappings` (choose the realm-level role)
  - For an activity manager, assign `activity-manager` role.

6) (Optional) Use groups for queue-based permissions
- The application models groups and queue permissions inside its own database (`UserGroup`, `QueuePermission`) rather than relying solely on Keycloak groups. If you prefer, you can mirror Keycloak groups into the application by using a mapper or by syncing group membership into the app.

Notes on roles and how the backend uses them
- The backend uses roles in these ways:
  - `admin` is checked to allow administrative endpoints (for example admin CRUD operations).
  - `activity-manager` was used in example tests to allow activity update/delete operations.
- The tests use a bypass (`KEYCLOAK_BYPASS = True`) and an `X-Test-User` header to impersonate a local DB user id instead of validating a real Keycloak token.

Recommended minimal role assignments
- Admin user: `admin`
- Regular user: no special realm role (can be member of groups inside the application DB)
- Activity organizer/manager: `activity-manager` (if you plan to gate activity update/delete in Keycloak)

Troubleshooting & verification
- After configuring Keycloak, test with a valid token and call an endpoint that requires authentication, for example GET `/me`:
  - Include Authorization: Bearer <token>
  - Token should include `sub`, `email`, `given_name`, `family_name`, and `realm_access.roles` (if roles assigned)
- If you see the backend raise `KEYCLOAK_BYPASS requires using get_current_user_bypass in route`, ensure `KEYCLOAK_BYPASS` is set to `False` in production. That message indicates the app was started with bypass enabled and the route called the non-bypass dependency.

Advanced: mapping client roles instead of realm roles
- If you prefer to manage roles per-client (client roles), create client roles under the `institution-client` and set a mapper to include `resource_access.<client-id>.roles` or adapt backend code to read client roles from token. Current backend reads `realm_access.roles`.

FAQ
- Q: Should agents be a Keycloak role?
  - A: Not strictly necessary. The backend stores `AgentAssignment` rows which control which users are agents for which queues. Using Keycloak roles for agents can help in the UI but duplicates authorization logic.

- Q: How to test locally?
  - A: Enable `KEYCLOAK_BYPASS=True` in `.env` or directly in `app/core/config.py` when running tests to allow `X-Test-User` header usage. For integration tests with Keycloak, run Keycloak locally and set `KEYCLOAK_SERVER_URL`/`KEYCLOAK_REALM` accordingly.

Appendix: Minimal claim example (access token payload snippet)

{
  "sub": "user-keycloak-uuid",
  "email": "user@example.com",
  "given_name": "First",
  "family_name": "Last",
  "realm_access": { "roles": ["user", "activity-manager"] }
}


---
This doc can be extended with step-by-step screenshots and an example realm JSON export if you want a reproducible realm import. If you'd like, I can produce a Keycloak realm export JSON (roles + client) tuned to this app.
