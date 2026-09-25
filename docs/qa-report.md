# QA Report

Date: 2026-09-25
Build: local source verification
Environment: Python 3.13, FastAPI/Uvicorn, local filesystem

## Frontend verification
- 83 HTML files present: 36 English content pages, 36 French content pages, 4 English error pages, 4 French error pages, 1 English admin page and 1 French admin page.
- Every English and French content page has a matching page-level CSS and JavaScript file.
- Separate admin CSS/JS files are used so admin code does not overwrite homepage code.
- Favicon, Apple touch icon, PWA icons and supplied logo variants are wired.
- Three supplied co-founder photographs are optimized WebP assets in the public team directory. Originals stay outside the public directory.
- French/English navigation, mobile menu, theme switcher, dialogs, forms, filters and language routes are present.
- Actuality, Careers, Newsletter, Contact and chatbot UI connect to stable backend contracts.

## Automated checks
- `python scripts/validate.py`: PASS. 83 HTML pages checked.
- `python scripts/test_site.py`: PASS. 70 linked public routes crawled for internal links, theme toggle and language switch behavior.
- `python scripts/test_overflow.py`: PASS. 22 core routes checked at 320, 375, 768, 1024, 1280, 1440 and 1920 px.
- `python scripts/test_api.py`: PASS. Health, public routes, robots, sitemap, real 404 and retired URL redirects checked.
- `python scripts/test_backend.py`: PASS. Temporary database admin MFA login, CSRF, Actuality publish, bilingual Actuality article route, dynamic sitemap inclusion and job publishing tested.
- `python scripts/security_scan.py`: PASS. 277 source and documentation files inspected for common secret patterns and public placeholder leakage.
- `python -m py_compile server.py`: PASS.

## Responsive and browser verification
The overflow harness used Chromium in the local environment and checked the required seven widths. The harness inlines local CSS because the sandbox browser blocks direct navigation to the local HTTP server. This verifies CSS layout behavior, but it is not a substitute for end-to-end production-browser verification.

Still required before publication: manual Chrome, Safari, Firefox and Edge checks, representative mobile-browser checks, keyboard and screen-reader walkthroughs, 200% and 400% zoom checks, and exact production-build verification.

## Security verification
Implemented locally: security headers, server-side admin authorization, MFA-based admin login, secure production session cookies, CSRF protection for authenticated mutations, rate limits, request validation, safe errors, private file storage, upload allowlist and signature checks, and required ClamAV fail-closed behavior in production mode.

Not verified locally: live TLS, HSTS on the production domain, exact production CORS policy, production CAPTCHA, SMTP delivery, ClamAV availability, external monitoring, backup restore, dependency vulnerability scan, independent security review or penetration test.

## Content and legal blockers
The company still needs to confirm official phone, email, domain, legal registration and tax information where required, privacy contact and legal representative, social accounts, office hours, newsletter frequency, recruitment retention period, legal page wording, team-photo ownership and consent, production email provider and approved CAPTCHA and malware-scanning services.

## Release status
The codebase is locally verified and structured for production integration. Public release remains blocked until the company-specific inputs, legal review, production services, final security checks and exact deployed-site verification pass.
