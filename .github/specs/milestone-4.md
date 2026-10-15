# Milestone 4: persistent storage and configurable expense rules

## Goal

Replace process-local dataset storage with durable database-backed storage using
an ORM, and let each account configure the expense categories and person
identification rules used during upload and reporting. This milestone prepares
the data model for multiple users; account authentication and ownership
enforcement are delivered in Milestone 5.

## Current state and motivation

Datasets and processed-upload cache entries currently live in process memory.
They disappear on restart and are not shared between application workers.
Categories are configuration-driven, while `who` detection is tied to
application-specific description patterns. These defaults are suitable for an
MVP, but users need durable datasets and a way to define their own categories
and explain how transactions map to people.

## Scope

- Select and document a supported relational database and Python ORM, keeping
  local development straightforward and production configuration explicit.
- Define ORM models and migrations for datasets, expense rows, and the
  per-user expense rules needed by Milestone 5.
- Replace the in-memory dataset store with a repository backed by the database.
  Preserve existing upload, summary, filtering, and export API behavior where
  possible.
- Persist uploaded/categorized expense records and the metadata required to
  identify and retrieve each dataset after process restarts.
- Define lifecycle and retention behavior for datasets and generated download
  files. Persistent data must not silently inherit the current in-memory TTL.
- Support configurable category names and a configured fallback category,
  validating categories consistently during categorization, filtering, and
  reporting.
- Support configurable `who` identification rules. Users should be able to
  specify how a transaction description or other available transaction fields
  identify a person. Keep the initial rule format constrained, validated, and
  understandable; do not execute arbitrary user-provided code or expressions.
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

- A dataset remains available after an application restart when the configured
  database is retained.
- Multiple app workers see the same persisted datasets.
- Database schema changes are managed through versioned migrations.
- Existing summary, filter, and export behavior is preserved, with regression
  coverage for database-backed storage and monetary precision.
- Users can configure category lists and a fallback category, and invalid
  category references produce clear validation errors.
- Users can configure supported `who` matching rules without code execution;
  tests cover matching, precedence, unmatched transactions, and invalid rules.
- Retention and deletion behavior for datasets and generated files is explicit
  and documented.

## Out of scope

- Login, registration, sessions, authorization, and cross-user access control;
  these belong to Milestone 5.
- Arbitrary scripting or unrestricted regular expressions as user-defined
  matching logic.
- A distributed cache unless a measured requirement justifies one.
