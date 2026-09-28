---
description: Standardize agent handling of validated changes
applyTo: "**"
---

## Agent workflow learnings

- After the relevant tests, lint, and type checks pass, standardize the delivery flow: review the diff, commit the focused changes using the repository's commit convention, publish the branch, and create a pull request with a concise summary of the problem, fix, and validation.
- For this Python project, validation must use `uv` commands consistently: run the smallest relevant `uv run pytest` target first, then `uv run ruff check` and `uv run ty check` for the changed code. Bare `pytest`, `ruff`, or `ty` invocations are not the repo standard and can miss the project-managed environment.
- When a fix changes behavior, add or adjust a focused test before implementation and keep the test specific to the regression being fixed; the repo expects fast, targeted validation over broad suites unless the change genuinely affects shared logic.
