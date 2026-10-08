# Production Hardening Plan

This plan outlines a pragmatic path to take the current FastAPI expense categorizer from MVP to a production-ready application with the minimum amount of complexity.

## Goals
- Improve reliability, safety, and operability without over-engineering.
- Keep the architecture simple: one FastAPI service, one external AI dependency, and minimal operational complexity.
- Make the app suitable for real deployment and day-to-day operations.

## Phase 1: Configuration hardening
- Centralize runtime configuration in a typed settings layer.
- Validate required environment variables at startup.
- Provide clear defaults where appropriate.
- Ensure secrets are never exposed in logs or errors.

## Phase 2: Logging and observability
- Add structured logging with request IDs and correlation context.
- Log key lifecycle events: startup, uploads, parse failures, categorization fallback, download access, unexpected errors.
- Avoid logging raw file contents or sensitive financial data.
- Expose health and readiness endpoints that reflect dependency health.

## Phase 3: Security hardening
- Add minimal authentication for protected routes.
- Enforce upload limits such as max file size and allowed file types.
- Keep secrets in environment variables or secret storage.
- Add basic rate limiting and request-size protection.

## Phase 4: Resilience and reliability
- Handle Gemini timeouts and upstream failures gracefully.
- Use deterministic fallback logic when AI classification fails.
- Add clear error responses for malformed uploads and processing failures.
- Make long-running operations fail safely and predictably.

## Phase 5: Deployment readiness
- Make temporary storage configurable and clean up files safely.
- Add containerization and a production startup command.
- Provide health checks and deployment guidance for reverse proxies and TLS termination.
- Keep the deployment model simple and operationally manageable.

## Phase 6: Testing and CI
- Add regression tests for auth, upload validation, timeout handling, and Gemini failure cases.
- Add linting and test automation in CI.
- Document local and operational verification steps.

## Suggested implementation order
1. Configuration and settings validation
2. Structured logging and request middleware
3. Authentication and upload hardening
4. Exception handling and resilience for external services
5. Health/readiness and basic metrics
6. Containerization and deployment documentation

## Files likely to change
- app/main.py
- app/config.py
- app/services/gemini_service.py
- pyproject.toml
- tests/

## Acceptance criteria for the overall plan
- The app exposes a health/readiness signal suitable for deployment monitoring.
- Invalid uploads fail with clear, non-500 responses.
- Gemini failures do not break the main request flow.
- Protected routes require authentication.
- Logs provide enough context for debugging without exposing secrets.
