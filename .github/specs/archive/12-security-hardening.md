# Issue 12: Strengthen application security

## Title
Harden the application against unsafe input, secret exposure, and common web risks

## Description
As the app moves toward production, it should protect against unsafe uploads, invalid input, secret leakage, and dependency-related risks. This issue covers basic security hardening to reduce exposure and provide safer defaults for users and operators.

## Scope
- Validate and constrain uploaded file types, size, and content where applicable
- Sanitize and validate any user-controlled input before processing
- Ensure secrets are loaded from environment variables or a secure config path
- Add dependency and package hygiene checks to reduce known-risk exposure
- Review and document security-sensitive settings and operational safeguards

## Acceptance Criteria
- Upload handling rejects unexpected or unsafe input patterns
- Sensitive configuration values are not exposed through application output
- The project has documented security expectations for local development and deployment
- Security-sensitive paths are covered by tests or validation checks
