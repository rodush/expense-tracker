---
description: Standardize agent handling of validated changes
applyTo: "**"
---

## Agent workflow learnings

- After the relevant tests, lint, and type checks pass, standardize the delivery flow: review the diff, commit the focused changes using the repository's commit convention, publish the branch, and create a pull request with a concise summary of the problem, fix, and validation. Treat this as standing user authorization; do not wait for separate approval. Skip publication only if the user opts out or a concrete blocker prevents safe delivery, and explain any blocker.
- For Python changes, use the project-managed `uv` environment: run the smallest relevant `uv run pytest` target first, then applicable Ruff and `ty` checks. Bare `pytest`, `ruff`, or `ty` invocations are not the repo standard.
- For frontend changes, run the frontend scripts from `frontend/`: `npm test`, `npm run check`, and `npm run build`. Do not use Python checks as a substitute for frontend validation.
- When a fix changes behavior, add or adjust a focused test before implementation and keep the test specific to the regression being fixed. Follow TDD for both stacks; prefer fast, targeted validation unless the change affects shared behavior.
- For changes spanning both stacks, validate both separately. Build the Docker image when frontend asset paths, packaging, or runtime delivery changes.
- After the pull-request is merged, make sure to cleanup work artifacts (git branch, git worktree) afterwards.
