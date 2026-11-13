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

This runs the app directly on your machine and does not require Docker,
Podman, or PostgreSQL. The SQLite `DATABASE_URL` below stores data in
`expense-tracker.db` in the project directory.

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
uv sync --group migration
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
PostgreSQL data in a named volume and waits for the database to become healthy.
Alembic migrations are run explicitly from the project environment before the
app starts; the runtime image does not contain migration tooling.

1. Copy the example environment file and edit it as needed:

   ```sh
   cp .env.example .env
   ```

   Supply the Gemini key through your shell environment, not `.env`. For
   example, export it in the terminal before starting or recreating the app:

   ```sh
   read -rsp "Gemini API key: " GEMINI_API_KEY
   export GEMINI_API_KEY
   printf '\n'
   ```

   Compose forwards this shell variable to the app container. Keep it exported
   in the same terminal when running `podman compose up`; if the app container
   already exists, recreate it to update its environment:

   ```sh
   podman compose up -d --no-build --force-recreate app
   ```

   Unset it when you no longer need it in the current shell with
   `unset GEMINI_API_KEY`. If the key is not set, the app uses the local
   categorization fallback. The example PostgreSQL password is for local
   development only; replace it if the database will be reachable outside your
   machine. Keep `.env` private and do not commit it. For host-side migrations,
   `DATABASE_URL` must use `127.0.0.1` and the published PostgreSQL port; the
   example file is already configured that way. If you have an older `.env`,
   change `DATABASE_URL` to
   `postgresql+psycopg://expense_tracker:local-dev-password@127.0.0.1:5432/expense_tracker`.
   Keep its username and password in sync with `POSTGRES_USER` and
   `POSTGRES_PASSWORD`. The app container gets its separate Compose-network
   URL automatically.

2. Start PostgreSQL from the repository root:

   ```sh
   podman compose up -d db
   podman compose ps
   ```

   The database is published on `127.0.0.1:5432` by default so host-side
   migration commands can connect to it. Confirm the `db` service is healthy
   before running the migration. Set `POSTGRES_PORT` in `.env` to use another
   local port.

3. From the project root, install the locked Python dependencies and apply
   migrations to that PostgreSQL database:

   ```sh
   uv sync --group migration
   uv run alembic upgrade head
   ```

   `DATABASE_URL` in `.env` points the host-side migration command at the
   published database port. If you change `POSTGRES_PORT`, update the port in
   `DATABASE_URL` to match. The database username and password in that URL
   must match `POSTGRES_USER` and `POSTGRES_PASSWORD`.

4. Build and start the application:

   ```sh
   podman build --format docker -t expense-categorizer:local .
   podman compose up -d --no-build app
   ```

   The app container uses `db:5432` on the Compose network; host-side Alembic
   uses `127.0.0.1` and the published port. On subsequent schema updates, run
   `uv run alembic upgrade head` from the project root before deploying the
   updated app image.

5. Open [http://127.0.0.1:8000](http://127.0.0.1:8000). To use another host
   port, set `APP_PORT` in `.env`; the app remains available on port 8000
   inside the container.

Useful commands:

```sh
podman compose ps
podman compose logs -f app
podman compose down
```

Stopping the containers does not remove the PostgreSQL data volume. To
permanently delete the database and all imported expense data, run
`podman compose down -v`.

## Deployment

The application listens on `0.0.0.0` in the container and uses the `PORT`
environment variable (default `8000`).

Build and run a production image with:

For deployment, set `DATABASE_URL` in the runtime environment to the durable
database used by the migration job. Do not rely on the image's default
container-local SQLite database for persistent production data.

```sh
docker build -t expense-categorizer .
docker run --rm -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL \
  -e CATEGORIES=Food,Transport,Utilities,Shopping,Other \
  -e GEMINI_API_KEY=YOUR_GEMINI_API_KEY \
  expense-categorizer
```

Apply database migrations as a separate deployment step, using a migration
job or release task with the same database configuration as the app. In CI/CD,
that job should check out the release's migration files, install the project's
migration group (`uv sync --locked --no-dev --group migration`), and run
`uv run alembic upgrade head` with `DATABASE_URL` supplied from the deployment's
secret store. Gate the app rollout on the migration job succeeding, and
coordinate so only one job migrates a database at a time. Do not run
migrations automatically in each application container's startup command.

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

This release has no authentication or dataset ownership enforcement. Run it only
on a trusted private network for one household. Compose and the Docker command
above publish the app on host loopback only. Use an SSH tunnel or a private VPN
for remote access; do not expose the port or forward a public reverse proxy to
it. Keep container networks private as well: containers on the same network can
reach the app directly. Public deployment requires account authentication and
object ownership checks first (milestone 5).

For a private server deployment, terminate TLS at the reverse proxy, pass secrets
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
