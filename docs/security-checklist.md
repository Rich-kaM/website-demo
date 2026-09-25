# Security checklist

A01 Broken Access Control: implemented for protected admin routes with server-side role checks. Manual horizontal and vertical privilege testing remains required on the production identity set.

A02 Security Misconfiguration: API docs disabled, production HSTS conditional on secure-cookie configuration, deny-by-default browser policies applied. Production reverse proxy and deployment configuration remain to verify.

A03 Software Supply Chain: dependency versions are pinned in requirements.txt. `pip-audit` is not installed in the local verification environment, so vulnerability scanning is not verified here. Add dependency scanning to CI before release.

A04 Cryptographic Failures: scrypt password hashing, HMAC token hashing, secure session cookies and TOTP are implemented. TLS depends on the production edge.

A05 Injection: Pydantic validation, parameterized SQLite queries, escaped dynamic Actuality rendering and controlled browser DOM updates are used.

A06 Insecure Design: trust boundaries, chatbot, contact, newsletter and upload flows are documented. Independent security review remains required.

A07 Authentication Failures: admin MFA, session expiry, login throttling and generic authentication errors are implemented. Password policy requires a minimum of 10 characters in the first-run setup.

A08 Software/Data Integrity: admin mutations are audited. No webhook integration exists in the current build.

A09 Logging & Alerting: selected admin actions are recorded in audit logs. Production monitoring, alert delivery and retention policy remain to configure.

A10 Exceptional Conditions: generic public errors, upload fail-closed scanning and rate limits are implemented. Production failure-path verification remains required.

Uploads: PDF/DOCX allowlist, file signature validation, content-type checks, 5 MB limit, random storage names, storage outside the web root and optional required ClamAV scanning are implemented.

ASVS 5.0.0: this checklist is a project-level map, not a formal certification. A qualified reviewer should complete the applicable ASVS assessment before launch.
