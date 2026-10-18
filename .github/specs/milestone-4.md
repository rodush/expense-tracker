# Milestone 4: persistent expense ledger and configurable rules

## Goal

Turn monthly ABN AMRO transaction exports into a durable, searchable expense
ledger. Store each processed expense independently of the file it came from,
avoid categorizing or storing the same transaction twice when exports overlap,
and let the user review historical expenses. This milestone prepares the data
model for multiple users; account authentication and ownership enforcement are
delivered in Milestone 5.

## Current state and motivation

The user exports transactions from ABN AMRO as an XLS file each month. They may
upload the same export again, or upload a later export that overlaps an earlier
period. Previously processed expenses must remain available indefinitely and
must not be categorized or counted twice. Categories and the rules that assign
an expense to a person need to be configurable. The user needs to browse the
combined history and filter it by category, person, and date, including quick
month/year selection.

## Scope

- Select and document a supported relational database and Python ORM, keeping
  local development straightforward and production configuration explicit.
- Define ORM models and migrations for import batches, persistent expense
  records, and the per-user expense rules needed by Milestone 5.
- Treat an uploaded file as an import batch, not as the boundary of the user's
  history. Query the ledger across all imports.
- Give each expense a stable deduplication key. Check existing keys before
  categorization, then enforce uniqueness in the database so repeated and
  overlapping imports do not add or process known expenses again.
- Prefer a stable transaction reference from the bank export when one is
  available. Otherwise use a documented fingerprint over normalized bank
  fields and preserve repeated identical rows within one import using an
  occurrence discriminator. A fingerprint cannot perfectly distinguish two
  truly identical transactions across different exports without a bank ID.
- Persist normalized expense date, amount, description, category, person, and
  source fields so history can be queried and reconstructed after restart.
- Add historical expense queries and exports that span imports and support
  category, person, inclusive date-range, and month/year filters.
- Keep the existing upload, summary, filtering, and export API behavior where
  practical, while making the historical ledger the canonical view.
- Define lifecycle and retention behavior for datasets and generated download
  files. Persistent data must not silently inherit the current in-memory TTL.
- Support configurable category names and a configured fallback category,
  validating categories consistently during categorization, filtering, and
  reporting.
- Support configurable `who` identification rules. Users should be able to
  specify how a transaction description or other available transaction fields
  identify a person. Keep the initial rule format constrained, validated, and
  understandable; do not execute arbitrary user-provided code or expressions.
- In this single-user milestone, read category and `who` settings from validated
  deployment configuration. Persisted per-user settings and their management
  flow depend on authenticated ownership and belong to Milestone 5.
- Provide migration, backup, and restore guidance appropriate to the selected
  database and deployment model.

## Design constraints

- Keep database access behind repository/service boundaries and preserve
  dependency injection for tests.
- Keep financial calculations in backend services and use decimal arithmetic
  for stored and aggregated money values.
- Ensure datasets and rule configurations can be associated with an owner, but
  do not consider an untrusted client-supplied owner identifier authorization.
  Milestone 5 must enforce ownership using the authenticated principal.
- Avoid logging transaction descriptions, uploaded rows, or sensitive rule
  values.
- Keep database credentials and provider settings in runtime configuration.

## Acceptance criteria

- Processed expenses remain available after an application restart when the
  configured database is retained; they do not expire.
- Multiple app workers see the same persisted datasets.
- Re-uploading the same file or overlapping exports skips known expenses,
  including avoiding repeat categorization for those records.
- Historical queries combine expenses across imports and can filter by
  category, person, date range, and selected month/year.
- Database schema changes are managed through versioned migrations.
- Existing summary and export behavior is preserved where practical, with
  regression coverage for database-backed storage, duplicate imports, date
  filters, and monetary precision.
- Category lists, fallback category, and supported `who` matching rules can be
  configured through deployment settings; invalid values produce clear startup
  errors. Tests cover matching, precedence, unmatched transactions, and invalid
  rules. Per-user setting management is delivered after authentication.
- Retention and deletion behavior for datasets and generated files is explicit
  and documented.

## Out of scope

- Login, registration, sessions, authorization, and cross-user access control;
  these belong to Milestone 5.
- Arbitrary scripting or unrestricted regular expressions as user-defined
  matching logic.
- A distributed cache unless a measured requirement justifies one.
