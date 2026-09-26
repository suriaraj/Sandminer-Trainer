# Security Baseline

- Argon2 password hashing.
- Short-lived JWT access tokens and separately signed refresh tokens.
- Server-side RBAC plus ownership/tenant scoping.
- No secrets in source; environment/secret manager only.
- CORS allow-list and security headers.
- Request-rate limiting is required at gateway/API layer before production.
- File uploads require extension + MIME + signature validation, malware/quarantine workflow and private object storage.
- Payment/KYC webhooks require signature verification, timestamp tolerance and replay protection.
- Logs redact authorization headers, cookies, tokens, KYC content, payment secrets and signed URLs.
- Admin financial actions must be auditable; high-value refund/settlement actions should support dual approval.
- IDOR tests are mandatory for booking, document and operator resources.

Production review must include SQL injection, XSS, CSRF where applicable, SSRF, CORS, privilege escalation, session invalidation, brute-force controls and sensitive-data exposure.
