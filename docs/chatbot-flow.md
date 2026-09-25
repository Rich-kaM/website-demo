# Chatbot flow

The visitor opens the chatbot from any page in French or English.

State 1. Welcome. The visitor sees the privacy reminder and the purpose of the chatbot.

State 2. Information collection. The UI collects full name, email, organization, service of interest, context, and consent. The full production workflow also needs the approved phone or WhatsApp, country or location, purpose, and preferred contact method when those fields are required by APAH.

State 3. Qualification. The server should apply only company-approved deterministic criteria. The current build stores the request without inventing a score.

State 4. Agent available. The production handoff channel must be connected after APAH supplies an approved live-chat, WhatsApp, phone, or agent system.

State 5. Agent unavailable. Store the lead and send an internal notification after the approved email is configured.

State 6. Request submitted. Show a translated success message.

State 7. Error. Show a generic, translated error without internal details.

Abuse controls include input length limits, endpoint rate limiting, generic public responses, consent, and server-side validation. Add a privacy-friendly CAPTCHA before launch when abuse risk and the legal review justify the service.

Admin workflow: authorized staff review leads, assign ownership, update status, and close requests. Audit logs record sensitive actions.
