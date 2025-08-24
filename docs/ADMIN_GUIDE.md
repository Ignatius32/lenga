# Admin Guide — Helpdesk & Space Manager

This guide explains how the Helpdesk and Space Management backend are organized and how an administrator can configure queues, groups, agents, ticket types, and related permissions. It also includes notes on testing, migrations, and common workflows.

## Overview

Key concepts:

- User: an identity persisted in the `users` table. In production, users are sourced from Keycloak; tests use a `KEYCLOAK_BYPASS` and `x-test-user` header to impersonate users.
- Role: label assigned to users (e.g., `admin`, `agent`). Roles are stored in `roles` and linked via `user_roles`.
- Group: collection of users (e.g., `Clients`, `Support Team`) used to grant queue posting permissions.
- Queue: a logical inbox for tickets (e.g., `Helpdesk`, `Facilities`). Agents are assigned to queues.
- AgentAssignment: ties a user to a queue with an access level (e.g., `Tier 1`, `Manager`). Determines what the agent may do within that queue.
- TicketType: preconfigured ticket templates attached to a queue; can include custom fields and allowed groups (which groups can create tickets of that type).
- Ticket: the main entity users create. Tickets have movements, comments, attachments, and a lifecycle (status changes, assignments).

## Entities and how they relate

This section defines the main domain entities and their relationships so you (the admin) can reason clearly about permissions and flows.

- Agent: a user who processes tickets. Conceptually an agent has two parts:
  - a Role (`agent`) assigned in `roles`/`user_roles` (grants access to agent API endpoints), and
  - one or more `AgentAssignment` rows that bind the user to specific queues with an `access_level` (controls capabilities inside each queue).

- Client: an end user who creates tickets. Clients are ordinary `User` rows that typically belong to a group (e.g., `Clients`) used to grant posting permission to queues.

- Group: a named collection of users. Groups are used for two main purposes:
  1. Queue permission: `QueuePermission` grants a group the right to post tickets into a queue.
  2. Ticket type restriction: a `TicketType` may declare `allowed_group_ids` to limit which groups can create tickets of that type.

- AgentAssignment: a tuple (agent_user_id, queue_id, access_level). This controls whether an agent is allowed to act on tickets in that queue (claim, assign, transfer, resolve). Example access levels: `Tier 1`, `Tier 2`, `Manager`.

- TicketType: a template owned by a queue. It can declare custom fields and a list of groups allowed to create that type. Ticket types help structure incoming tickets and enforce field validation.

- Ticket: belongs to a `current_queue_id`, may have a `current_agent_id`, and references a `ticket_type_id` (optional). Ticket lifecycle events are recorded in `TicketMovementLog`.

Relationships (summary):

- User 1..* <---> 0..* UserGroup (user belongs to groups)
- Group 1..* <---> 0..* QueuePermission (group may be allowed in queues)
- Queue 1..* <---> 0..* AgentAssignment (agents assigned to queues)
- TicketType 1..* <---> 0..* TicketTypeAllowedGroup (ticket types may restrict allowed groups)
- Ticket 1..* <---> 0..* TicketMovementLog / TicketComment / Attachment

How they work together (practical view):

- When a client creates a ticket they must: belong to a group that has permission on the selected queue, and if they choose a ticket type it must allow one of their groups.
- Agents only operate on tickets belonging to queues where they have an `AgentAssignment`. Their `access_level` determines special rights (e.g. transfer rights).
- Admins control all configuration: they create queues, groups, add users to groups, create ticket types and fields, and assign agents to queues.


The API is implemented with FastAPI. Models live in `app/models/models.py` and REST endpoints are under `app/api/`.

## Admin responsibilities and common tasks

The following sections show step-by-step operations and which endpoints to call. All admin endpoints are under `/admin` and require the `admin` role (or tests use `KEYCLOAK_BYPASS` with an admin `x-test-user`).

### 1) Create and manage groups

- Create a group:
  - POST `/admin/groups` with JSON: `{ "name": "Clients", "description": "Client users" }`
  - Returns group object `{ id, name, description }`.

- Add a user to a group:
  - POST `/admin/groups/{group_id}/users` with JSON: `{ "user_id": <user_id> }`.

- Remove a user from a group:
  - DELETE `/admin/groups/{group_id}/users/{user_id}`.

Use groups to control which users may post into queues and which ticket types they can create.

### 2) Create queues and grant posting permissions

- Create a queue:
  - POST `/admin/queues` with JSON: `{ "name": "Helpdesk", "description": "Helpdesk queue" }`.

- Grant a group permission to post into a queue:
  - POST `/admin/queue_permissions` with JSON: `{ "group_id": <group_id>, "queue_id": <queue_id> }`.

- Revoke group permission:
  - DELETE `/admin/queue_permissions` with the same JSON payload.

Queue permissions ensure that only users belonging to permitted groups can create tickets in a queue.

### 3) Create ticket types (templates) with custom fields

Ticket types let you define structured tickets, including custom fields.

- Create a ticket type attached to a queue and allowed groups:
  - POST `/admin/ticket_types` with JSON:
    {
      "queue_id": <queue_id>,
      "name": "General Inquiry",
      "allowed_group_ids": [<group_id>, ...],
      "fields": [
        { "name": "Severity", "field_type": "select", "options": ["Low", "High"] },
        { "name": "Location", "field_type": "space" }
      ]
    }

  - The response contains the ticket type with field IDs which clients may use when creating tickets.

- Update ticket type:
  - PUT `/admin/ticket_types/{ticket_type_id}` with `TicketTypeUpdate` payload. Passing `fields` replaces existing fields and cleans up stored values.

- Delete ticket type:
  - DELETE `/admin/ticket_types/{ticket_type_id}` — fails if existing tickets reference the type.

Notes about custom fields:
- Field types supported: `text`, `select`, `space`.
- `select` fields store `options` (array) as JSON in the DB. When creating a ticket, the API rejects values not present in `options`.
- `space` fields expect a space ID (ensure the space exists in `spaces` table).

### 4) Add agents and assign them to queues

An `agent` is simply a user with the `agent` role plus an `AgentAssignment` to one or more queues.

- Assign an agent to a queue (admin):
  - POST `/admin/agents/assign` with JSON: `{ "agent_user_id": <user_id>, "queue_id": <queue_id>, "access_level": "Tier 1" }`.
  - Response: the created AgentAssignment object with `id`, `agent_user_id`, `queue_id`, `access_level`.

- Unassign an agent:
  - DELETE `/admin/agents/assign/{agent_assignment_id}`.

- Convenience endpoints to give a user the `agent` role and remove it (admin-only):
  - POST `/admin/roles/make_agent` with `{ "user_id": <user_id> }` — assigns the `agent` role.
  - POST `/admin/roles/remove_agent` with `{ "user_id": <user_id> }` — removes the `agent` role.

Access levels and transfer rules:
- `access_level` is a free-form string in the DB (common values used: `Tier 1`, `Tier 2`, `Manager`).
- Agent action authorization checks use `access_level` when transferring/assigning tickets; managers (or assignments with `allow_transfer`) may transfer tickets.

### 5) Typical ticket lifecycle and agent actions

Endpoints for agent actions are under `/agents/` and generally require the agent to be assigned to the ticket's current queue.

- Claim a ticket:
  - POST `/agents/tickets/{ticket_id}/claim` — claims a ticket so `current_agent_id` becomes the agent. The endpoint logs a `CLAIM` movement.

- Assign ticket to another agent (acting agent must have appropriate rank):
  - POST `/agents/tickets/{ticket_id}/assign` with JSON `{ "target_agent_id": <id> }`. Logs `ASSIGN` movement.

- Transfer ticket to another queue:
  - POST `/agents/tickets/{ticket_id}/transfer` with JSON `{ "target_queue_id": <queue_id>, "reason": "..." }`. The acting agent must be assigned to the source queue and be Manager or have `allow_transfer` on their assignment. Logs `TRANSFER_QUEUE` movement, clears `current_agent_id`.

- Change status / resolve:
  - PATCH `/agents/tickets/{ticket_id}/status` with JSON `{ "status": "Resolved", "resolved_at": "<iso datetime>" }`. Logs `STATUS_CHANGE` movement.

- Post a comment (agent):
  - POST `/agents/tickets/{ticket_id}/comments` with `{ "comment_text": "...", "is_internal": false }`.
  - Logs `COMMENT` movement and returns the created comment. Internal comments are flagged via `is_internal` and may be omitted from client views in a future UI.

### 6) Attachments

- Upload an attachment (authenticated user/agent):
  - POST `/attachments/upload?ticket_id=<ticket_id>` with a multipart form field `file`. The server stores the file under `./uploads` (see `app/core/storage.py`) and creates an `Attachment` row with `file_path`.

Notes:
- The upload endpoint stores files locally in `./uploads`. For production, adapt `app/core/storage.py` to use an S3-compatible store or other durable storage.
- Uploaded attachments are included in the ticket history response (see history below).

### 7) Ticket creation by clients (non-admin)

- Endpoint: POST `/tickets/` with JSON `{ "subject": "...", "description": "...", "queue_id": <queue_id>, "ticket_type_id": <optional> }`.
- Preconditions:
  - User must belong to at least one group that has a `QueuePermission` for the target `queue_id`.
  - If `ticket_type_id` is provided and it has `allowed_group_ids`, the user's groups must intersect that allowed list.
  - If `custom_fields` are provided in the ticket creation payload, the server validates them against the ticket type's fields (`select` options, `space` ids) and persists `TicketFieldValue` rows.

### 8) Viewing ticket and history

- Get ticket: GET `/tickets/{ticket_id}` — only the ticket creator can view a ticket via this endpoint (agents have separate agent endpoints for agent views).
- Ticket history: GET `/tickets/{ticket_id}/history` — returns `movements`, `comments`, and `attachments`. Accessible by the ticket creator, agents assigned to the ticket's current queue, or admins.

The `TicketHistoryOut` response includes nested brief user objects for `action_user`, `author` and `uploader` where present.

## Testing locally (KEYCLOAK_BYPASS)

The test suite uses a bypass so token verification and Keycloak calls are avoided. In the tests:

- `settings.KEYCLOAK_BYPASS = True` is used to enable bypass.
- The bypass dependency expects an `x-test-user` header containing a numeric user id from the local DB (created in tests using the models).
- When using the bypass, the dependency collects roles from `user_roles` to simulate user roles like `admin` or `agent`.

Use the `tests/conftest.py` pattern when writing tests — it overrides `get_db` to use an in-memory sqlite and sets the bypass flag.

## Migrations

Migrations are managed by Alembic (directory `alembic/versions/`). If you add or change models:

1. Update `app/models/models.py`.
2. Run `alembic revision --autogenerate -m "message"` to create a new migration. Review the autogenerated file.
3. Apply with `alembic upgrade head`.

Important: If you used `Base.metadata.create_all()` on an existing DB (development convenience), Alembic autogenerate may produce an empty migration or conflicting operations. In that case either:
- Use `alembic stamp head` to mark the database as up to date and then create new migrations moving forward; or
- Manually edit the migration to match the intended operations.

## Operational notes and best practices

- Roles and assignment separation: Roles (`agent`, `admin`) are separate from queue assignments: granting a user the `agent` role alone doesn't allow them to act on tickets until they are assigned to a queue via `AgentAssignment`.
- Access-level semantics: Access levels are used as a simple rank for actions such as assigning or transferring tickets. For advanced policies, extend `AgentAssignment` with explicit permission fields (e.g., `allow_transfer`, `can_resolve`).
- Attachments storage: Replace `LocalStorage` with cloud storage in production.
- Data cleanup: Ticket types cannot be deleted while tickets reference them. Deleting fields will delete stored values.
- Logging/movement: Ticket actions are recorded in `TicketMovementLog`. Use these logs to build audit trails in the UI.

## Example admin flow (quick recipe)

1. Create group `Clients` and add users.
2. Create queue `Helpdesk`.
3. Grant `Clients` permission on `Helpdesk`.
4. Create `General Inquiry` ticket type for `Helpdesk`, allowed for `Clients`.
5. Assign `agent` role to support users and assign them to `Helpdesk` with access levels.
6. Ask a client to create a ticket; agent claims it; agent responds with a comment and attaches files; manager transfers to another queue if necessary and resolves ticket.

## Where to look in the code

- Models: `app/models/models.py`
- Schemas (payload shapes): `app/schemas.py`
- Admin endpoints: `app/api/admin.py`
- Ticket endpoints: `app/api/tickets.py`
- Agent endpoints (claim/assign/transfer/comment/status): `app/api/agents.py`
- Attachments: `app/api/attachments.py`
- Security & test bypass: `app/core/security.py`
- Storage backend (local implementation): `app/core/storage.py`

## FAQ / Troubleshooting

- I'm seeing `KEYCLOAK_BYPASS requires using get_current_user_bypass in route`: That means `settings.KEYCLOAK_BYPASS = True` but the route depends on `get_current_user`. Change the route to use `get_current_user_bypass` for tests, or disable bypass.

- Uploaded files not found in tests: The attachments endpoint stores files under `./uploads`. Tests that upload files will write into that directory; consider cleaning it between runs.

- Alembic autogenerate doesn't create expected revisions: Ensure DB doesn't already have the new tables from `create_all`, or `alembic stamp` appropriately.

---

If you'd like, I can:
- Add a short checklist with exact example `curl`/httpie commands for each admin operation.
- Create a simple admin HTML page that talks to these endpoints (a very small single-page UI) to manage queues and ticket types.
- Add tests to verify admin flows like group->queue permissions and ticket-type restrictions.

Tell me which of those you'd like next and I'll implement it.