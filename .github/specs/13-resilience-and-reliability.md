# Issue 13: Improve resilience to failures and transient issues

## Title
Make the application more reliable under external failures and degraded conditions

## Description
The app depends on external services and file-processing steps that can fail unpredictably. This issue focuses on making the system resilient by handling retries, timeouts, partial failures, and clear fallback behavior without crashing the whole workflow.

## Scope
- Add timeout handling for external service calls and long-running operations
- Implement retry logic for transient errors where appropriate
- Gracefully handle failures during parsing, categorization, or file processing
- Provide clear user-facing error states and recovery guidance
- Avoid leaving the app in a half-initialized or inconsistent state

## Acceptance Criteria
- Transient failures are handled with retries or controlled fallback behavior
- Long-running operations do not hang indefinitely
- Errors are surfaced clearly to users and operators
- Recovery behavior is covered by tests or documented operational guidance
