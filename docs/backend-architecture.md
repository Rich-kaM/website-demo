# Backend architecture

The frontend uses stable HTTP contracts so page-level code stays independent of the backend implementation.

Public endpoints

`GET /api/health` returns service health.

`GET /api/csrf` issues a CSRF token for an authenticated browser session.

`POST /api/contact` stores a lead from the Contact page.

`POST /api/chat` stores a chatbot lead after consent.

`POST /api/newsletter/subscribe` creates a pending subscription and sends a single-use confirmation token.

`GET /newsletter/confirm` confirms a subscription only with a valid, unexpired token.

`GET /newsletter/unsubscribe` marks a subscription as unsubscribed.

`POST /api/applications` accepts a PDF or DOCX CV up to 5 MB and stores the file outside the public web root.

`GET /api/actuality` returns published Actuality items.

`GET /api/jobs` returns published job postings.

Admin endpoints

`POST /api/admin/login`, `POST /api/admin/logout`, `GET /api/admin/data`, `PATCH /api/admin/leads/{id}`, `PATCH /api/admin/applications/{id}`, `POST /api/admin/actuality`, and `POST /api/admin/jobs`. Publishing status is restricted to Admin or Approver roles.

Authentication uses server-side sessions with high-entropy random session tokens, hashed storage, expiration, HttpOnly cookies, SameSite=Lax, and secure cookies in production. Passwords use `hashlib.scrypt`. Admin login requires a time-based one-time password generated from the stored TOTP secret.

SQLite stores users, sessions, leads, newsletter subscribers and tokens, applications, Actuality, jobs, audit logs, and rate-limit state.

The backend applies security headers, request limits on public abuse-sensitive endpoints, server-side validation, generic errors, and safe private upload storage.

Email uses SMTP from environment variables. In development, an email preview is written to the server log. In production, the newsletter route fails closed when SMTP is missing so the website does not claim double opt-in without sending a confirmation email.

Multi-instance deployment should move rate limiting and uploaded files to shared infrastructure before horizontal scaling.

Career uploads are checked by extension, file signature, content type and size. When `UPLOAD_SCAN_REQUIRED=1` or production mode is active, a configured ClamAV service is required and the upload path fails closed when the scanner is unavailable. Files stay outside the public web root.
