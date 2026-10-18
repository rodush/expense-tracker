# Expense Categorizer

Expense Categorizer turns monthly ABN AMRO transaction exports into a persistent household expense ledger. It assigns each expense a category and a person, skips records already imported, and lets you browse spending history across all uploads.

The repository contains a Svelte frontend in [`frontend/`](./frontend/) and a
FastAPI backend in [`app/`](./app/), deployed together as a Docker container.

GitHub Actions run the frontend checks, Python checks, and Docker image build on
pull requests.

## Monthly import and expense history

The workflow is:

1. **Upload**: send a CSV, XLS, or XLSX file to `POST /upload`. It must contain
   date, amount, and description columns. ABN AMRO headers `Transactiedatum`,
   `Transactiebedrag`, and `Omschrijving` map to those fields.
2. **Import once**: the server normalizes expenses, resolves who made each
   expense, categorizes only records not already in the ledger, and stores the
   result in the configured database. Identical files are recognized by their
   content hash; overlapping exports are checked record by record.
3. **Browse history**: the dashboard combines records from every import. Filter
   by category, person, date range, or quick month/year selection. Export the
   filtered results or the full history.

Positive amounts (credits) and SEPA transfers to `Savings Account` are excluded
before categorization; retained debits are stored as positive spending amounts.
Expenses and their categories do not expire. Database records survive process
restarts and are shared by app instances using the same database. Without a
stable bank transaction reference, record fingerprints cannot distinguish
truly identical transactions across different exports; see the
[Milestone 4 specification](./.github/specs/milestone-4.md).

## Python application structure

`app/main.py` creates the FastAPI application and wires its services. Upload
and dataset endpoints live in separate routers; their processing and reporting
logic is handled by `UploadService` and `DatasetService` in `app/services/`.
Routers obtain these services with FastAPI dependencies, so tests can replace
them through `app.dependency_overrides` without patching application globals.
`create_app` accepts injected stores, categorizer, person resolver, and output
directory for explicit application-level wiring.

`POST /upload` returns `row_count`, `new_transaction_count`, `duplicate_count`,
`category_column_added`, `columns`, `preview`, `download_id`, and `dataset_id`.
The preview includes newly stored rows for the import; repeat uploads report
zero new records and do not categorize known transactions again.

## Reporting API contract

Historical expenses are queried across all import batches:

```text
GET /expenses
GET /expenses/summary
GET /expenses/filter-options
GET /expenses/export
```

Repeated query parameters select multiple values:

```text
?category=Food&category=Transport&who=Roman&date_from=2026-01-01&date_to=2026-01-31
```

`GET /expenses` returns a paginated `items` list with `total_count`, `limit`,
and `offset`. The summary response contains:

- `total_amount`: the sum of selected expenses.
- `expense_count`: the number of selected rows.
- `categories`: category name, amount, count, and percentage.
- `who`: person name, amount, and count.
- `applied_filters`: the validated category, person, and date selection.

Use repeated `category` and `who` query parameters for multiple selections,
`date_from` and `date_to` for inclusive date ranges, or `year` and optional
`month` for quick calendar filtering. Values within one filter use OR
semantics; different filters combine with AND semantics. Filters may return
zero matches without error. `/expenses/export` exports the same filtered
historical records.

## Frontend application

The dynamic upload, historical filtering, download, and dashboard UI is
implemented in Svelte with Vite. This is a client-side component application,
not a SvelteKit application: FastAPI continues to serve the page, APIs, and
compiled assets under `/static/frontend/`. Chart.js is bundled locally, so the
browser does not load frontend code from a third-party CDN.

The category doughnut chart updates with the selected filters and assigns a
distinct color to each category in the summary response. The historical expense
table is paginated. Its Description column is last and
constrained to about 300 pixels; hovering or focusing a description reveals
its full text in a viewport-aware tooltip.

To build assets for local development:

```bash
cd frontend
npm ci
npm run build
cd ..
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The build writes generated files to `app/static/frontend/`; they are ignored
by Git. The Docker image builds them in a Node.js stage and copies them into
the FastAPI image.

## Amounts, empty results, and exports

- Amounts are parsed as numeric values during upload. Positive values are
  treated as card credits, and SEPA transfers whose description names
  `Savings Account` are excluded before categorization. Retained negative debit
  values are stored and reported as their absolute values. Thus the ledger
  contains expenses only, and `total_amount` is a gross spending total.
- The ledger currently assumes one currency. Currency metadata and mixed
  currency handling need to be defined before importing accounts with multiple
  currencies.
- A valid filter that matches no rows is not an error. It returns
  `total_amount: 0`, `expense_count: 0`, and empty breakdowns.
- `/expenses/export` exports the filtered ledger. `/download/{download_id}`
  remains available for a full categorized CSV associated with one import.

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

### Tech stack

- Python + FastAPI + SQLAlchemy for backend and persistence
- Svelte 5+ (not SvelteKit) for the frontend, with Vite for building and the
  frontend test/check tools declared in `frontend/package.json`
- PicoCSS for styling
- SQLite by default; PostgreSQL is supported for hosted deployments

## Run locally

Build the frontend, then start FastAPI from the repository root:

```bash
cd frontend
npm ci
npm run build
cd ..
uv run fastapi dev
```

Then open:

```text
http://127.0.0.1:8000
```

## Deployment

The application listens on `0.0.0.0` in the container and uses the `PORT`
environment variable (default `8000`). Build and run a production image with:

```bash
docker build -t expense-categorizer .
docker run --rm -p 8000:8000 \
  -e CATEGORIES=Food,Transport,Utilities,Shopping,Other \
  -e GEMINI_API_KEY=YOUR_GEMINI_API_KEY \
  expense-categorizer
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
apply Alembic migrations before serving traffic. SQLite is the default for
local and single-host deployments; see the database guide before choosing a
multi-host deployment database.

Database setup, migrations, production configuration, backup/restore, and
current expense/download retention behavior are documented in
[`docs/database.md`](./docs/database.md).

## Environment variables

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

Application logs are emitted as one JSON object per line by default. Set
`LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`; set
`LOG_FORMAT=text` for human-readable local output. Logs include request IDs,
HTTP method/path, status, duration, and operation metadata, but never include
API keys or uploaded file contents.

## Category config

Categories and deterministic `who` matching rules are deployment-level
configuration for this milestone. Per-account settings management will build
on the persisted configuration model after authentication is introduced.

The category list is read from `CATEGORIES` and the fallback from
`FALLBACK_CATEGORY`; the fallback must be one of the configured categories.
`TRANSACTION_DATE_FORMAT` uses Python `strptime` directives and defaults to
`%Y%m%d`, matching the ABN AMRO export's `YYYYMMDD` date values. For another
bank format, configure its corresponding format (for example `%d-%m-%Y`).
`WHO_RULES` is a JSON array of literal, case-insensitive substring rules in
first-match order. Each rule contains exactly `contains` and `who`, for example:

```json
[{"contains":"card ending 1234","who":"Alex"}]
```

Rules are bounded and validated at startup; regular expressions and executable
expressions are not accepted. `WHO_UNMATCHED_LABEL` names transactions that
match no rule. If no who rules are configured, existing Roman/Oksana matching
defaults are retained.

- Food
- Transport
- Utilities
- Shopping
- Other

## Testing

In the project root directory run

```bash
cd frontend
npm ci
npm run lint
npm run format:check
npm test
npm run check
npm run build
cd ..
uv run pytest
uv run ruff format --check
uv run ruff check
uv run ty check
```

CI runs frontend linting, formatting verification, tests, Svelte diagnostics,
and the production build for every pull request and for pushes to `master`.
Run `npm run format` from `frontend/` to apply Prettier formatting. ESLint uses
the official Svelte plugin with its recommended rules. The test suite does not require a Gemini API key; external
categorization is covered with deterministic fallbacks and mocks.

The release gate also includes API contract tests
for category-only, person-only, combined, multi-value, invalid-filter,
unknown-import, malformed-amount, negative-amount, and empty-result cases.
Manually verify upload initialization, filter reset, loading/error/empty
states, chart/table/download consistency, and safe text rendering of uploaded
descriptions.

## TODO

### Persistence and rollout notes

Expense records use the configured relational database and do not expire.
Account ownership enforcement, user-visible retention/deletion, currency
metadata, and automated cleanup remain future production work. See
[`docs/database.md`](./docs/database.md) for setup, migrations, backup/restore,
and current lifecycle boundaries. Import batches record upload metadata; the
ledger is the canonical source for history, summaries, and historical exports.
