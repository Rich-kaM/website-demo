# Security architecture

Trust boundaries: browser to HTTPS edge, edge to FastAPI application, application to SQLite/private files, application to SMTP provider.

Sensitive assets: admin credentials, TOTP secrets, session tokens, CSRF tokens, application files, lead data, newsletter consent records, audit logs.

Authentication: server-side session cookies. Admin requires password plus TOTP. No admin API trusts hidden UI state.

Authorization: admin endpoints resolve the current session server-side and reject unauthenticated requests. Role values are stored server-side.

Sessions: high-entropy random tokens, HMAC-hashed at rest, expiration, logout invalidation, HttpOnly cookie, Secure cookie in production, SameSite=Lax.

CSRF: authenticated state-changing routes require a server-issued CSRF token. Public non-cookie data routes do not depend on frontend-only permission checks.

Uploads: allow only PDF and DOCX, 5 MB maximum, signature checks, random storage names, private storage outside the public directory, attachment download behavior. Malware scanning remains a launch integration item.

HTTP defenses: CSP, HSTS in production, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy.

Secrets: all secrets use environment configuration. `.env` is ignored by Git.

Abuse protection: endpoint rate limits, input length constraints and outbound email failure-closed behavior in production.

Open production work: distributed rate limiting, full CAPTCHA enforcement, malware scanning, independent security review, managed backups, restore testing, reverse proxy configuration, and production deployment verification.

Upload security: career files are allowlisted to PDF/DOCX, signature-checked, size-limited, stored outside public web content, and sent to ClamAV when upload scanning is required. Production should set UPLOAD_SCAN_REQUIRED=1 and configure CLAMAV_HOST/CLAMAV_PORT or CLAMAV_SOCKET.
