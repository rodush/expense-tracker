---
applyTo: "**"
---

# AGENTS.md

## Sensitive instructions for AI coding agents

This repository is a Python-based project. Treat all changes as production-adjacent and follow these rules strictly.

### 1. Security and secrets
- Never hardcode credentials, tokens, API keys, private endpoints, personal data, or secrets.
- Do not commit `.env`, `.venv`, local secrets, or generated credentials.
- If a sample configuration is needed, use placeholders like `YOUR_API_KEY` and clearly mark them as non-production.
- Prefer environment variables or secure configuration loaders over inline secrets.

### 2. Dependency hygiene
- Before adding a new Python package, confirm it is necessary and minimal.
- Prefer well-maintained, widely used libraries with a clear security track record.
- Do not downgrade dependencies or change lockfiles unless required by the task.
- Keep dependency changes scoped to the request and document why they are needed.

### 3. Code safety and correctness
- Preserve the existing architecture, style, and conventions unless the task explicitly requires refactoring.
- Make the smallest safe change that solves the user’s request.
- Do not introduce new runtime behavior without a corresponding test or justification.
- Avoid unsafe filesystem writes, shell execution, or network calls outside the explicitly requested scope.

### 4. Python-specific guidance
- Use Python v3.14.
- Use uv as package manager.
- Follow PEP 8 and existing project formatting standards.
- Prefer type hints, clear docstrings, and readable naming where appropriate.
- Avoid broad exception swallowing. Fail loudly and handle expected errors explicitly.
- Use `pathlib`, `logging`, and standard library tooling where possible instead of ad hoc patterns.
- Keep imports sorted and remove unused imports.
- Create clean idiomatic Python code
- Avoid spaghetti-code, structure business logic into re-usable functions and modules

### 5. Data handling
- Treat all customer, financial, and personal data as sensitive.
- Do not log raw secrets, access tokens, or PII.
- Avoid writing temporary files into shared directories unless the task requires it.

### 6. Testing and validation
- Follow TDD approach.
- Run the relevant tests for any Python change when feasible.
- When fixing an issue make sure the broken test is created first, and make sure it passes after the fix is implemented.
- Do not claim tests pass unless they were actually run.

### 7. Change discipline
- Do not make unrelated cleanup changes.
- Do not rewrite large sections of code without a clear reason.
- If a request is ambiguous, choose the least risky interpretation and keep the diff focused.

### 8. Final review checklist
Before finishing, verify:
- No secrets or sensitive data were introduced.
- No unrelated files were modified.
- The change is minimal, justified, and consistent with the repository’s Python conventions.
- Any tests or validation steps actually performed are reported accurately.
