# Issue 11: Add structured logging and observability

## Title
Introduce consistent logging, diagnostics, and operational visibility

## Description
The application needs production-grade logging so operators can understand failures, trace requests, and investigate issues quickly. This issue covers adding structured logs, standard log levels, request context, and safe error reporting without leaking secrets.

## Scope
- Add structured application logging across key workflows
- Standardize log levels for startup, request handling, parsing, categorization, and failures
- Include useful context such as request IDs, file names, and operation status
- Ensure logs do not expose secrets, tokens, or raw sensitive content
- Provide clear guidance for local and deployed log configuration

## Acceptance Criteria
- Core application flows emit structured logs with consistent formatting
- Errors and warnings are logged with sufficient context for debugging
- Sensitive data is redacted from logs
- Logging configuration is documented and configurable per environment
