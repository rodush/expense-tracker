# Expense Categorizer

Expense Categorizer turns monthly ABN AMRO transaction exports into a persistent household expense ledger. It assigns each expense a category and a person, skips records already imported, and lets you browse spending history across all uploads.

The repository contains a Svelte frontend in [`frontend/`](./frontend/) and a
FastAPI backend in [`app/`](./app/), deployed together as a Docker container.

## Tech stack

- Python + FastAPI + SQLAlchemy for backend and persistence
- Svelte 5+ (not SvelteKit) for the frontend, with Vite for building and the
  frontend test/check tools declared in `frontend/package.json`
- PicoCSS for styling
- SQLite by default; PostgreSQL is supported for hosted deployments
- GitHub Actions as a CI/CD server (runs the frontend, Python checks, and Docker image build on pull requests)

## Contribution

### Prerequisites

In order to contribute to the project, you need to have the following ecosystem:
- Python v3.14+
- Node.js 24.15+ and npm
- uv (Install as per your OS way)
- git (Install as per your OS way)
- github cli tool [gh](https://cli.github.com/)
- [trufflehog](https://github.com/trufflesecurity/trufflehog)
- [Github Agentic Workflows](https://github.com/github/gh-aw) extension
- Docker container. We use [podman](https://podman.io/)

## Run locally

### Environment variables

Create a `.env` file (`cp .env.example .env`) or export the following variables:

```bash
export GEMINI_API_KEY=YOUR_GEMINI_API_KEY
export CATEGORIES=Food,Transport,Utilities,Shopping,Other
export FALLBACK_CATEGORY=Other
export TRANSACTION_DATE_FORMAT=%Y%m%d
export WHO_RULES='[{"contains":"card ending 1234","who":"Alex"}]'
export WHO_UNMATCHED_LABEL=General
export DATABASE_URL=sqlite:///./expense-tracker.db
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

### Build and run applications

1. Build the frontend (from `frontend` subfolder):

```sh
cd frontend
npm ci
npm run build
```

2. Run database migrations (from the root of the project):

```sh
cd ..
uv run alembic upgrade head
```

3. Start FastAPI (from the repository root):

```sh
uv run fastapi dev
```

Website will open at:

```text
http://127.0.0.1:8000
```

You can just click the link in TUI, and default web browser will open the page.

## Run with containers (PostgreSQL)

The Compose setup runs the app and PostgreSQL in separate containers. It keeps
PostgreSQL data in a named volume, waits for the database to become healthy,
and applies Alembic migrations before starting the app.

1. Copy the example environment file and edit it as needed:

   ```sh
   cp .env.example .env
   ```

   Set `GEMINI_API_KEY` to your key, or leave it empty to use the local
   categorization fallback. The example PostgreSQL password is for local
   development only; replace it if the database will be reachable outside your
   machine. Keep `.env` private and do not commit it.

2. Start the containers from the repository root.

   With Docker Compose:

   ```sh
   docker compose up --build -d
   ```

   With Podman, first build in Docker format so the image retains the
   Dockerfile health check, then start Compose without rebuilding:

   ```sh
   podman build --format docker -t expense-categorizer:local .
   podman compose up -d --no-build
   ```

   `podman compose` requires an installed Compose provider, such as
   `podman-compose` or Docker Compose.

3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000). To use another host
   port, set `APP_PORT` in `.env`; the app remains available on port 8000
   inside the container.

Useful commands:

```sh
docker compose ps
docker compose logs -f app
docker compose down
```

For Podman, replace `docker compose` with `podman compose`. Stopping the
containers does not remove the PostgreSQL data volume. To permanently delete
the database and all imported expense data, run `docker compose down -v` (or
`podman compose down -v`).

## Deployment

The application listens on `0.0.0.0` in the container and uses the `PORT`
environment variable (default `8000`).

Build and run a production image with:

```sh
docker build -t expense-categorizer .
docker run --rm -p 8000:8000 \
  -e CATEGORIES=Food,Transport,Utilities,Shopping,Other \
  -e GEMINI_API_KEY=YOUR_GEMINI_API_KEY \
  expense-categorizer
```

### NOTE on Podman

When building container with `podman`, you might get warning:

> WARN[0092] HEALTHCHECK is not supported for OCI image format and will be ignored. Must use `docker` format

The right command is:

```sh
podman build --format docker -t expense-categorizer .
```

The image builds the frontend with the locked npm dependencies and uses the
locked Python dependencies from `uv.lock`. It does not enable Uvicorn's
development reload mode and includes a Docker health check. Use
`GET /health` for liveness and `GET /ready` for readiness monitoring. Both
endpoints are local-runtime checks and do not replace an external load balancer
or process supervisor.

For a server deployment, terminate TLS at the reverse proxy, pass secrets
through the hosting platform's secret store rather than an image or committed
file, and forward traffic only after `/ready` returns `200`. Set
`LOG_FORMAT=json` for structured logs and configure `LOG_LEVEL` according to
the platform's logging policy. Set `DATABASE_URL` to a durable database and
apply Alembic migrations before serving traffic.
SQLite is the default for local and single-host deployments;
see the database guide before choosing a multi-host deployment database.

Database setup, migrations, production configuration, backup/restore, and
current expense/download retention behavior are documented in
[`docs/database.md`](./docs/database.md).

## CI/CD

Once code is pushed to remote Github repository and pull-request is opened,
the corresponding workflow of Github Actions is triggered.

Workflow perform frontend linting, formatting verification, tests, Svelte diagnostics,
and the production build for every pull request and for pushes to `master`.
Run `npm run format` from `frontend/` to apply Prettier formatting. ESLint uses
the official Svelte plugin with its recommended rules. Prettier is configured
to keep Svelte template text wrapping readable. The test suite does not require
a Gemini API key; external
categorization is covered with deterministic fallbacks and mocks.

The release gate also includes API contract tests
for category-only, person-only, combined, multi-value, invalid-filter,
unknown-import, malformed-amount, negative-amount, and empty-result cases.
Manually verify upload initialization, filter reset, loading/error/empty
states, chart/table/download consistency, and safe text rendering of uploaded
descriptions.

## TODO

- [] Account settings
- [] Ability to manually configure categories and "who" rules in the Account
- [] Ability to overwrite, manually change the pre-assigned category
- [] Ideally, integration with the Bank API, but it's not feasible as requires PSD compliance.
- [] Re-use build artifact, or consider not running build as part of PR, only type checking.
