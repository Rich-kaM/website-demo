# Accessibility checklist

Target: WCAG 2.2 AA.

Verified in the local frontend gate:
- Semantic landmarks, skip links and heading hierarchy are present on core pages.
- Keyboard focus styles are visible.
- Theme and language controls expose accessible labels.
- Dialogs support Escape close and return focus.
- Forms expose labels, status regions and consent text.
- Responsive checks ran at 320, 375, 768, 1024, 1280, 1440 and 1920 px using the local overflow harness.

Still required before public release:
- Manual screen-reader walkthrough in French and English.
- Color contrast audit on the exact production build.
- Browser-specific keyboard and zoom checks at 200% and 400%.
