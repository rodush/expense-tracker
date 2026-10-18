# Milestone 5: authentication and multi-user support

## Goal

Make the application safe for multiple users by adding authentication and
enforcing ownership of datasets, expense records, generated downloads, and
per-user categorization rules persisted in Milestone 4.

## Scope

- Choose and document an authentication approach suitable for the intended
  public deployment, including account creation or invitation, login, logout,
  credential recovery, and session/token lifecycle as applicable.
- Add a persistent user identity model and securely store credentials or
  identity-provider references. Never store plaintext passwords or expose
  authentication secrets in logs or responses.
- Require authentication for all user data and configuration endpoints,
  including upload, dataset summary/filter/export, and categorized downloads.
- Associate every dataset, uploaded expense record, generated download, and
  category/`who` configuration with its owning user.
- Derive ownership from the authenticated principal on the server. Do not
  trust user IDs, dataset ownership, or access scopes supplied by request bodies
  or query parameters.
- Enforce object-level authorization on reads, updates, exports, and deletes;
  a user must not be able to access another user's resources by guessing an ID.
- Define account deletion and data-retention behavior, including cleanup of
  owned datasets and generated files where required.
- Add protections appropriate to the selected authentication design, such as
  secure cookie settings and CSRF defenses for cookie sessions, or token
  expiration and rotation for token-based authentication.
- Update frontend flows and API error handling for unauthenticated and
  unauthorized requests.

## Design constraints

- Reuse the database and migration approach established in Milestone 4.
- Keep authentication and authorization behind FastAPI dependencies and
  service-level ownership checks, so tests can inject principals and stores.
- Return consistent errors without revealing whether another user's resource
  exists.
- Apply least privilege to administrative operations and avoid adding a public
  self-service admin role by default.
- Keep authentication provider secrets in secure runtime configuration.

## Acceptance criteria

- Anonymous requests cannot access protected user data or configuration.
- Authenticated users can access their own datasets and rules, and cannot read,
  modify, export, download, or delete another user's resources.
- Ownership is checked consistently across all API routes and generated-file
  paths.
- Credentials, sessions, and recovery flows follow the documented security
  model, with focused regression tests for authentication and object ownership.
- User data lifecycle and account deletion behavior are documented and tested.
- Deployment and local-development instructions explain required auth settings
  without including real credentials.
