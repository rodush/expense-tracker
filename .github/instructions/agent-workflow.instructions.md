---
description: Standardize agent handling of validated changes and transient Gemini failures.
applyTo: "**"
---

## Agent workflow learnings

- After the relevant tests, lint, and type checks pass, standardize the delivery flow: review the diff, commit the focused changes using the repository's commit convention, publish the branch, and create a pull request with a concise summary of the problem, fix, and validation.
- External Gemini calls can raise `google.api_core.exceptions.GoogleAPICallError`, including `DeadlineExceeded`, rather than a built-in `TimeoutError`. Catch that API error at the categorization retry boundary so transient failures receive the configured retries and then use the documented heuristic fallback instead of crashing the request.
