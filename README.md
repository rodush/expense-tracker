# Expense Categorizer

This project is a small FastAPI-based expense categorization app that reads uploaded CSV/XLS/XLSX files and assigns categories using a configurable category list with Gemini support.

The repository contains a Svelte frontend in [`frontend/`](./frontend/) and a
FastAPI backend in [`app/`](./app/), deployed together as a Docker container.

GitHub Actions run the frontend checks, Python checks, and Docker image build on
pull requests.

## Reporting workflow

The reporting workflow is designed as:

1. **Upload**: the browser sends an expense file to `POST /upload`. The file
   must contain `date`, `amount`, and `description` columns. ABN AMRO headers `Transactiedatum`, `Transactiebedrag`, and `Omschrijving` are mapped to those English field names during processing.
   
   The service normalizes column names, excludes rows with positive amounts (card credits) and SEPA transfers to
   `Savings Account` before categorization, converts retained debit amounts to
   absolute values, derives `who`, assigns a configured category, and returns a preview. The response's `row_count`, preview, dataset, and downloads contain only the retained rows.
   Identical input bytes and file types reuse processed rows from a one-hour in-memory cache, avoiding repeat categorization.
2. **Dataset**: the response includes a short-lived `dataset_id` for the
   normalized rows. The dataset is the shared source for the preview,
   summaries, and exports; it is not a second copy with different parsing
   rules.
3. **Dashboard**: clients request an aggregate summary for that dataset and
   redraw totals, breakdown tables, and charts when filters change.

The implementation provides a temporary full CSV download through
`GET /download/{download_id}` and the dataset-backed summary endpoint below.
The browser dashboard uses the same dataset and summary contract for its
filter controls, tables, and chart.

## Python application structure

`app/main.py` creates the FastAPI application and wires its services. Upload
and dataset endpoints live in separate routers; their processing and reporting
logic is handled by `UploadService` and `DatasetService` in `app/services/`.
Routers obtain these services with FastAPI dependencies, so tests can replace
them through `app.dependency_overrides` without patching application globals.
`create_app` also accepts the stores, cache, categorizer, and output directory
for explicit application-level wiring.

`POST /upload` returns `row_count`, `category_column_added`, `columns`,
`preview`, `download_id`, and `dataset_id`. `row_count` and `preview` include
only retained rows, and each returned `amount` is a nonnegative numeric value.
The download and dataset contain those same rows and amounts.

## Reporting API contract

The summary endpoint is:

```text
GET /datasets/{dataset_id}/summary
```

Repeated query parameters select multiple values:

```text
?category=Food&category=Transport&who=Roman&who=General
```

The response contains:

- `total_amount`: the sum of the selected retained expenses.
- `expense_count`: the number of selected rows.
- `categories`: category name, amount, count, and percentage.
- `who`: person name, amount, and count.
- `applied_filters`: the validated category and person selections.

Category values are validated against `CATEGORIES`. Person values are
validated against the people present in the dataset. Multiple values for one
filter are combined with OR semantics; category and `who` filters are combined
with AND semantics. No filter means all rows in the dataset. An unknown
dataset returns 404; invalid filters or malformed amounts return a clear 400
response, and a dataset must never be used to read another dataset's rows.

This contract aligns with the reporting specifications in
[`.github/specs/archive/16-dataset-and-summary-api.md`](.github/specs/archive/16-dataset-and-summary-api.md)
and [`.github/specs/milestone-2.md`](.github/specs/milestone-2.md). If the API
implementation requires a field change, update those documents and this
section together.

## Frontend application

The dynamic upload, preview, filtering, download, and dashboard UI is
implemented in Svelte with Vite. This is a client-side component application,
not a SvelteKit application: FastAPI continues to serve the page, APIs, and
compiled assets under `/static/frontend/`. Chart.js is bundled locally, so the
browser does not load frontend code from a third-party CDN.

The category doughnut chart updates with the selected filters and assigns a
distinct color to each category in the summary response. The categorized
expense preview is collapsed by default. Its Description column is last and
constrained to about 300 pixels; hovering or focusing a description reveals
its full text in a viewport-aware tooltip.

To build assets for local development:

```bash
cd frontend
npm ci
npm run build
cd ..
uv run uvicorn app.main:app --reload
```

The build writes generated files to `app/static/frontend/`; they are ignored
by Git. The Docker image builds them in a Node.js stage and copies them into
the FastAPI image.

## Amounts, empty results, and exports

- Amounts are parsed as numeric values during upload. Positive values are
  treated as card credits, and SEPA transfers whose description names
  `Savings Account` are excluded before categorization. Retained negative debit
  values are stored and reported as their absolute values. Thus uploaded
  datasets contain expenses only, and `total_amount` is a gross spending total.
- The reporting response should use one currency per uploaded dataset. Currency
  metadata and the final display precision must be defined before production
  persistence; aggregation and displayed totals must use the same rounding
  rule.
- A valid filter that matches no rows is not an error. It returns
  `total_amount: 0`, `expense_count: 0`, zero-valued configured-category
  breakdowns, and an empty `who` breakdown.
- The existing download is a full categorized CSV generated from the same
  normalized rows as the preview. A filtered export is not available yet and
  must be introduced as a separate, explicit action or endpoint rather than
  silently changing the meaning of the existing download link.

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

- Python + FastAPI for backend; (TODO: SqlAlchemy as ORM)
- Svelte 5+ (not SvelteKit) for the frontend, with Vite for building and the
  frontend test/check tools declared in `frontend/package.json`
- PicoCSS for styling
- TODO: PostgreSQL as DB (persistence layer)

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
current dataset/download retention behavior are documented in
[`docs/database.md`](./docs/database.md).

## Environment variables

Create a `.env` file (`cp .env.example .env`) or export the following variables:

```bash
export GEMINI_API_KEY=YOUR_GEMINI_API_KEY
export CATEGORIES=Food,Transport,Utilities,Shopping,Other
export FALLBACK_CATEGORY=Other
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
npm test
npm run check
npm run build
cd ..
uv run pytest
uv run ruff format --check
uv run ruff check
uv run ty check
```

CI runs the formatting, lint, and test commands for every pull request and for
pushes to `master` branch. The test suite does not require a Gemini API key; external
categorization is covered with deterministic fallbacks and mocks.

The release gate also includes API contract tests
for category-only, person-only, combined, multi-value, invalid-filter,
unknown-dataset, malformed-amount, negative-amount, and empty-result cases.
Manually verify upload initialization, filter reset, loading/error/empty
states, chart/table/download consistency, and safe text rendering of uploaded
descriptions.

## TODO

### Persistence and rollout notes

Datasets use the configured relational database and do not expire by default.
Account ownership enforcement, user-visible retention/deletion, currency
metadata, and automated cleanup remain future production work. See
[`docs/database.md`](./docs/database.md) for setup, migrations, backup/restore,
and current lifecycle boundaries. Summary, preview, and export continue to use
the same normalized dataset boundary.
