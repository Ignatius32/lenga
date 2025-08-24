# Institution Manager - Phase 1
```markdown
# Institution Manager

FastAPI backend with Keycloak authentication (production) and a dev bypass mode for local testing.

This repo contains admin SPA assets under `www/` and backend code under `app/`.

Quick start (development)

1. Create and activate a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run migrations (if using a persistent DB)

```bash
PYTHONPATH=$PWD alembic revision --autogenerate -m "add models"
PYTHONPATH=$PWD alembic upgrade head
```

4. Run in dev mode (bypass Keycloak locally)

```bash
export KEYCLOAK_BYPASS=1
export DATABASE_URL=sqlite:///./dev.db
uvicorn app.main:app --reload
```

5. Open the admin SPA: http://127.0.0.1:8000/admin
	- Use the Dev X-Test-User widget (top-right) to set your test id (e.g. `1`). The app will auto-create a minimal test user with the `admin` role when needed in dev mode.

Tests

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

Contributing

- Fork and open PRs. Add tests for new behavior.
- CI is welcome (I can add a GitHub Actions workflow if you want).

License: MIT (adjust as required)
```

