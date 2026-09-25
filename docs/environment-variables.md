# Environment variables

| Variable | Purpose | Exposure |
|---|---|---|
| APP_ENV | development or production behavior | server-only |
| APP_SECRET | HMAC secret for sessions, CSRF and token hashes | server-only |
| COOKIE_SECURE | enables Secure session cookies | server-only |
| APP_BASE_URL | public base URL used in email links | server-only |
| HOST | Uvicorn bind host | server-only |
| PORT | Uvicorn port | server-only |
| SMTP_HOST | SMTP server | server-only |
| SMTP_PORT | SMTP port | server-only |
| SMTP_USERNAME | SMTP account | server-only |
| SMTP_PASSWORD | SMTP password | server-only |
| SMTP_FROM | approved sender address | server-only |
| NOTIFY_EMAIL | approved internal notification address | server-only |
| SMTP_DAILY_LIMIT | outbound email budget | server-only |
| APPLICATION_RETENTION_DAYS | recruitment retention configuration | server-only |
| OPTIONAL_CAPTCHA_PROVIDER | approved CAPTCHA provider name | server-only |
| OPTIONAL_CAPTCHA_SECRET | CAPTCHA private key | server-only |
| CLAMAV_HOST | ClamAV TCP host for upload scanning | server-only |
| CLAMAV_PORT | ClamAV TCP port, normally 3310 | server-only |
| CLAMAV_SOCKET | ClamAV Unix socket, alternative to host/port | server-only |
| UPLOAD_SCAN_REQUIRED | require malware scanning for uploads, set to 1 in production | server-only |

No real values belong in source control.
