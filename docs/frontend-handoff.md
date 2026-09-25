# Frontend handoff

Frontend implementation is complete for the current approved information architecture.

Status:
- English and French HTML, CSS and JavaScript files exist per page.
- Normal and Dark Theme controls are implemented with first-party preference storage.
- Mobile navigation, language switching, dialogs, filters, forms, error pages and accessibility foundations are implemented.
- Supplied company logo assets and three supplied team photos are used.
- Backend-dependent contact, chatbot, newsletter, careers and Actuality behaviors use local API contracts.

Verification completed:
- `python scripts/validate.py`
- `python scripts/test_site.py`
- `python scripts/test_overflow.py`
- `python scripts/test_api.py`

Important limitation:
- The overflow test uses a local Playwright harness with inlined local CSS because the sandbox Chromium runner blocks direct navigation to the local HTTP server.

Backend phase commands:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/create_admin.py
python server.py
```
