# Architecture

It is a monolith multi-tier application: frontend, backend, database storage.

Frontend application is served from the same server which powers API and business logic.

It uses relational database (SQLite on local, PostgreSQL in Production) to store processed data persistently.
ORM is used to abstract database access.

For the sake of speeding this up, it uses in-memory, read-through, caching for repeated reads.


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

## Deployment access boundary

The current ledger belongs to one trusted household; authentication and per-account
ownership remain milestone 5 work. Deploy only on a trusted private network.
The supplied Compose mapping publishes HTTP on host loopback. Remote access must
use an SSH tunnel or private VPN, with no public proxy forwarding to the service.
All history, dataset, upload, download, and WebSocket routes share this boundary.
Container networks must also be restricted to trusted workloads.

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

See section of the main [README.md](/README.md) file for the commands.

The build writes generated files to `app/static/frontend/`; they are ignored
by Git. The Docker image builds them in a Node.js stage and copies them into
the FastAPI image.

## Logging standards

Application logs are emitted as one JSON object per line by default.

Set `LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.\
Set `LOG_FORMAT=text` for human-readable local output.

Logs include request IDs, HTTP method/path, status, duration, and operation metadata,
but never include API keys, uploaded filenames, or uploaded file contents.

PII is masked in the logs.

## ADR's

See [ADR.md](./adr.md) file.

