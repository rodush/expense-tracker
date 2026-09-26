# Expense Categorizer MVP

This project is a small FastAPI-based expense categorization app that reads uploaded CSV/XLS/XLSX files and assigns categories using a configurable category list with Gemini support.

## Reporting workflow

The reporting workflow is designed as:

1. **Upload**: the browser sends an expense file to `POST /upload`. The file
   must contain `date`, `amount`, and `description` columns. The service
   normalizes column names, derives `who`, assigns a configured category, and
   returns a preview.
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

- `total_amount`: the net sum of the selected rows.
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
[`.github/specs/16-dataset-and-summary-api.md`](.github/specs/16-dataset-and-summary-api.md)
and [`.github/specs/milestone-2.md`](.github/specs/milestone-2.md). If the API
implementation requires a field change, update those documents and this
section together.

## Amounts, empty results, and exports

- Amounts are parsed as signed numeric values. Negative values are retained as
  refunds or credits, so `total_amount` is a net total rather than a gross
  spending total.
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
- Python v3.14+ (soon will be 3.15)
- uv (Install as per your OS way)
- git (Install as per your OS way)
- github cli tool [gh](https://cli.github.com/)
- [trufflehog](https://github.com/trufflesecurity/trufflehog)
- [Github Agentic Workflows](https://github.com/github/gh-aw) extension

## Run locally

```bash
cd /home/rodush/Work/expense-tracker
/home/rodush/.local/bin/uv run uvicorn app.main:app --reload
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

The image uses the locked dependencies from `uv.lock`, does not enable
Uvicorn's development reload mode, and includes a Docker health check. Use
`GET /health` for liveness and `GET /ready` for readiness monitoring. Both
endpoints are local-runtime checks and do not replace an external load balancer
or process supervisor.

For a server deployment, terminate TLS at the reverse proxy, pass secrets
through the hosting platform's secret store rather than an image or committed
file, and forward traffic only after `/ready` returns `200`. Set
`LOG_FORMAT=json` for structured logs and configure `LOG_LEVEL` according to
the platform's logging policy. The in-memory dataset store is temporary and
is not safe to use as durable storage across restarts or multiple workers.

## Environment variables

Create a `.env` file or export the following variable:

```bash
export GEMINI_API_KEY=YOUR_GEMINI_API_KEY
export CATEGORIES=Food,Transport,Utilities,Shopping,Other
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

Application logs are emitted as one JSON object per line by default. Set
`LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`; set
`LOG_FORMAT=text` for human-readable local output. Logs include request IDs,
HTTP method/path, status, duration, and operation metadata, but never include
API keys or uploaded file contents.

## Category config

The starter category list is read from the `CATEGORIES` environment variable. If the variable is not set, the app falls back to:

- Food
- Transport
- Utilities
- Shopping
- Other

## Testing

```bash
cd /home/rodush/Work/expense-tracker
uv run pytest
uv run ruff format --check
uv run ruff check
uv run ty check
```

CI runs the formatting, lint, and test commands for every pull request and for
pushes to `main`. The test suite does not require a Gemini API key; external
categorization is covered with deterministic fallbacks and mocks.

The release gate also includes API contract tests
for category-only, person-only, combined, multi-value, invalid-filter,
unknown-dataset, malformed-amount, negative-amount, and empty-result cases.
When dashboard controls are added, manually verify upload initialization,
filter reset, loading/error/empty states, chart/table/download consistency,
and safe text rendering of uploaded descriptions.

## Persistence and rollout notes

The initial reporting dataset is intentionally short-lived and server-side. It
is currently held in process memory for one hour, with a UUID-like identifier.
This is suitable for the MVP only: process restarts, multiple workers, and
cleanup failures must be treated as expected limitations, not as durable
storage guarantees.

Before production use, replace the temporary repository with a database-backed
expense/session model. Define ownership or access control, retention and
deletion, currency metadata, migrations, indexing, and cleanup jobs as part of
that change. Keep the summary, preview, and export paths on the same normalized
dataset boundary so persistence does not introduce reporting discrepancies.
