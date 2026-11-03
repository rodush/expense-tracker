## Category config

Categories and deterministic `who` matching rules are deployment-level
configuration for this milestone. Per-account settings management will build
on the persisted configuration model after authentication is introduced.

## Transaction author config

`WHO_RULES` is a JSON array of literal, case-insensitive substring rules in
first-match order. Each rule contains exactly `contains` and `who`, for example:

```json
[{"contains":"card ending 1234","who":"Alex"}]
```

Rules are bounded and validated at startup; regular expressions and executable
expressions are not accepted. `WHO_UNMATCHED_LABEL` names transactions that
match no rule. If no who rules are configured, existing Roman/Oksana matching
defaults are retained.

- Food
- Transport
- Utilities
- Shopping
- Other