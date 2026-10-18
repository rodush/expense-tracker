# Agent instructions

These instructions apply to the whole repository. Keep changes focused, preserve
the existing architecture, and follow the language-specific guidance below.

## Project overview

This is a Python and Svelte project:

- Python 3.14, `uv`, FastAPI, pandas, and Gemini integration implement the API
  and expense processing.
- Svelte 5+ with Vite implements the browser UI. FastAPI serves the page and
  built frontend assets; it remains the API server. This is not a SvelteKit app
  and does not run a separate frontend server in production.
- Python source lives in `app/`; frontend source, npm manifests, and its lockfile
  live in `frontend/`; tests live in `tests/` and `frontend/`.
- Built frontend assets are generated under `app/static/frontend/` and served
  through FastAPI's `/static` mount. Do not edit generated build output by hand.

The README documents current API behavior and domain rules. Treat API contracts,
financial calculations, and expense filtering rules as sensitive behavior: keep
frontend expectations aligned with backend responses.

## General safety and change discipline

- Never add credentials, tokens, API keys, private endpoints, or personal data
  to source, tests, logs, or committed configuration. Use environment variables
  and placeholders for examples. Do not commit `.env`, virtual environments,
  `node_modules`, or generated credentials.
- Treat uploaded financial and personal data as sensitive. Do not log raw file
  contents, descriptions, or secrets.
- Make the smallest change that solves the task. Avoid unrelated cleanup,
  broad rewrites, and new runtime behavior without tests or clear justification.
- Do not add dependencies without confirming they are needed. For new or
  upgraded dependencies, choose the newest stable version compatible with the
  project at implementation time, check the library's current official docs,
  update the appropriate lockfile, and explain any compatibility constraint.
- Preserve dependency reproducibility. Do not install packages into or commit
  root-level `node_modules`; npm manifests and lockfiles belong in `frontend/`.
- Keep code modular and readable. Put API access, UI components, and reusable
  behavior in appropriately scoped frontend modules rather than growing one
  monolithic component.

## Python and FastAPI

- Use Python 3.14 and `uv`. Follow PEP 8 and the repository's Ruff formatting.
- Use type hints, clear names, `pathlib`, and standard-library facilities where
  appropriate. Avoid broad exception swallowing and unused imports.
- Use the latest stable FastAPI version compatible with the project and prefer
  its current response models, dependency injection, and typing features.
- Keep HTTP routing in `app/routers/`, business logic in `app/services/`, and
  service access behind FastAPI dependencies. Preserve dependency injection so
  tests can replace external services and stores.
- Do not move business rules into the browser. The frontend should call the
  existing API and render its responses.
- Before changing an API contract, inspect its callers and tests, update the
  relevant API documentation/specification, and add focused regression tests.

### Python validation

Run commands from the repository root using `uv`:

```sh
uv run pytest
uv run ruff format --check
uv run ruff check
uv run ty check
```

For a focused Python change, run the relevant test target first, then the
applicable Ruff and `ty` checks. Do not claim a check passed unless it ran.

## Frontend (the `frontend/` subproject)

- `frontend/package.json` and `frontend/package-lock.json` are the sole npm
  manifest and lockfile. Run npm commands from `frontend/`.
- Use Node.js 24.15 or newer for frontend development and CI.
- Use Svelte 5 or newer and current stable Vite/Svelte tooling compatible with
  the project's Node version. Use Svelte 5 runes (`$state`, `$derived`,
  `$effect`, and `$props`) for new reactive component code. Do not introduce
  legacy `$:` reactive declarations in new code; migrate legacy code touched by
  a change when it is practical and in scope.
- Keep state in Svelte components or Svelte-native state abstractions. Avoid
  mutable plain-JavaScript module globals as a substitute for reactive state.
- Use small `.svelte` components for cohesive UI areas and plain `.js` modules
  for API clients or framework-independent utilities. Do not add SvelteKit or a
  client-side router unless a task specifically requires one.
- Keep frontend code accessible and safe: use semantic HTML, preserve keyboard
  interaction, render uploaded values as text, and never inject untrusted HTML.
- FastAPI serves compiled files from `app/static/frontend/`; Vite's production
  output must target this directory. Docker must copy that output into the
  Python runtime image. Keep generated output out of version control.

### Frontend development and validation

Run from `frontend/`:

```sh
npm ci
npm run lint
npm run format:check
npm run format  # apply formatting fixes
npm test
npm run check
npm run build
```

ESLint uses the flat configuration in `frontend/eslint.config.js`, including
the recommended Svelte rules. Prettier uses the Svelte plugin; run
`npm run format` to fix formatting and `npm run format:check` to verify it.
The Prettier configuration sets `htmlWhitespaceSensitivity` to `ignore` for
more readable Svelte template wrapping.
Keep all frontend quality scripts in `frontend/package.json` and run lint,
format verification, tests, Svelte diagnostics, and the production build in CI.
Write or update a focused frontend test before changing behavior (TDD). If a
command cannot run because of an environment limitation, report that clearly
and do not imply it passed. Do not use `uv` to validate frontend-only changes.

For changes that touch both stacks, run the relevant Python and frontend
validation separately, and build the Docker image when packaging or static
asset paths change.

## Security and secrets

- Never hardcode credentials, tokens, API keys, private endpoints, or personal
  data. Use environment variables or a secure runtime configuration source.
- Treat uploaded files and their content as untrusted. Validate them on the
  server, escape/render their values safely, and avoid logging their contents.
- Do not add unsafe filesystem writes, shell execution, or network calls outside
  the task's scope.

## Agent workflow and delivery

- Work on a focused branch/worktree for each independent change. Preserve
  pre-existing user changes and inspect the complete diff before delivery.
- After relevant validation passes, commit focused changes using the repository
  commit convention, push the branch, and open a concise pull request. This is
  standing authorization. If publication is blocked, report the concrete
  blocker rather than claiming delivery.
- Monitor the pull request's required status checks after pushing and keep
  working until they pass. Inspect failed job logs, fix failures caused by the
  change, run the relevant checks locally, push the fix, and re-check the PR.
  Do not treat a failed or pending check as green. If a check fails only because
  an external AI service exhausted its credits or rate limit, record that
  limitation clearly; continue fixing any other actionable failures.
- In the final report, summarize what changed and why, list checks actually
  run, and link to the pull request. Do not claim tests or builds passed unless
  they were run successfully.
