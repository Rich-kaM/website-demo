# Africa Power Advisory Holding website

This repository contains the bilingual French and English website frontend, a FastAPI backend, protected application storage, a SQLite data model, the public chatbot lead flow, newsletter double opt-in flow, recruitment upload flow, admin session security, and the documentation required for local verification.

## Stack

Python 3.13, FastAPI, Uvicorn, SQLite, browser-native HTML/CSS/JavaScript, and the supplied APAH logo and team photographs. The site avoids unnecessary client-side frameworks so pages stay independently editable and fast.

## Local setup in VS Code

```bash
cd apah-production-site
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m playwright install chromium
cp .env.example .env
python scripts/create_admin.py
python server.py
```

Open `http://127.0.0.1:8000/`.

Health check: `http://127.0.0.1:8000/api/health`

## Environment

Copy `.env.example` to `.env` and set real values outside source control. Production secrets must live in the hosting provider secret manager.

## Admin first run

```bash
python scripts/create_admin.py
```

The script creates an admin account with a strong password and a TOTP secret. Store the password and TOTP secret in a password manager. The TOTP secret is shown once during setup.

Admin pages:
`/admin/en/` and `/admin/fr/`

## Test commands

```bash
python scripts/validate.py
python scripts/test_api.py
python scripts/test_overflow.py
python scripts/test_backend.py
python scripts/security_scan.py
```

`validate.py` checks page inventory, language pairs, title and description presence, placeholder leakage, local assets, favicon links, year rendering hooks, and source cleanliness.

`test_api.py` starts the app through Uvicorn and checks health, redirects, robots, sitemap, public pages, and a real 404 response.

`test_overflow.py` uses Playwright with the installed Chromium browser and checks the main routes at 320, 375, 768, 1024, 1280, 1440, and 1920 px widths.

## Production deployment

Use a Python hosting service such as Render, Railway, Fly.io, a managed VM, or another HTTPS server that supports FastAPI and persistent private storage.

Build step:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

Use a persistent volume for `/data` and `/private/uploads`, or move those stores to managed database and private object storage before a multi-instance deployment.

Set `COOKIE_SECURE=1`, `APP_ENV=production`, `APP_SECRET`, `APP_BASE_URL`, SMTP values, and approved notification addresses in the hosting provider secret manager.

Place a trusted reverse proxy in front of Uvicorn. Terminate TLS there. Confirm HSTS only after HTTPS works on every production route.

## GitHub

Before the first push:

```bash
git init
git add .
git status
git diff --cached
git grep -nE '(ghp_|github_pat_|AKIA[0-9A-Z]{16}|BEGIN (RSA|EC|OPENSSH) PRIVATE KEY|SMTP_PASSWORD=|APP_SECRET=)' -- . || true
git commit -m "Initial APAH production website"
git branch -M main
git remote add origin <approved-repository-url>
git push -u origin main
```

Do not commit `.env`, the database, production uploads, logs, or private original photographs.

## Content and launch inputs still required

The source specification forbids invented corporate data. Before public launch, the company must confirm the official telephone number, official email, website domain, registration and tax details where required, privacy contact and legal representative, official social accounts, actual office hours, newsletter frequency and topics, recruitment retention period, legal-page wording, photograph ownership and consent records, and the image/license source for any photo-led hero.

The supplied three photographs are present in the public team area only after optimization. The original files also sit outside the public directory under `private-assets/original-team/` for internal review. Replace those private copies with a controlled originals repository before handoff to the live server.

For production career uploads, configure ClamAV and keep `UPLOAD_SCAN_REQUIRED=1`. The application fails closed for uploads when scanning is required but unavailable.
