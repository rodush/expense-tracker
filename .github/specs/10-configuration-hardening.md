# Issue 10: Harden configuration management

## Title
Strengthen configuration loading, validation, and environment handling

## Description
The application should treat configuration as a first-class production concern. This issue covers defining required settings, validating them at startup, documenting expected values, and preventing invalid or missing configuration from causing ambiguous runtime failures.

## Scope
- Define required and optional environment variables for local development and production
- Validate configuration values early with clear error messages
- Provide sensible defaults where appropriate
- Ensure secrets and sensitive values are never logged or exposed in error output
- Document configuration expectations for contributors and operators

## Acceptance Criteria
- Required configuration values are validated at startup
- Invalid or missing settings fail fast with actionable error messages
- Configuration is documented in a discoverable location
- Sensitive values are excluded from logs and diagnostics
