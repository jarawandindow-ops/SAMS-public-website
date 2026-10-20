# SAMS website forms and email safeguards
**Operational pilot settings · 20 October 2026**

## Administrative inbox
sam.support.admin@gmail.com is the intended recipient of general, non-sensitive public enquiries, expressions of interest and partnership messages.

## Current live pilot
- General enquiry, volunteer and partnership forms prepare pre-addressed drafts in the visitor's **own email app**.
- The visitor must press **Send**. No message is sent merely by clicking a website button.
- Only non-sensitive contact information and a selected enquiry topic are included in those drafts.
- The website does not silently store public submissions, medical histories or case notes.
- Where no email program is configured, visitors can email the SAMS address directly.
- A secure server-to-email delivery system is **not configured** and must not be advertised as working.

## Production requirements for automatic sending
1. An organisation-controlled sender and authorised email API/SMTP account.
2. Environment-managed credentials (never committed to GitHub or included in HTML).
3. Sender authentication (SPF, DKIM and preferably DMARC for a custom sender domain).
4. Server-side input validation, origin and CSRF controls as applicable, honeypot/rate limiting and abuse monitoring.
5. Consent and purpose-specific privacy notice; minimal non-sensitive information only.
6. No identifiable health narratives or sensitive documents sent to the general Gmail inbox.
7. Separate secured CRM handling for any confidential support request, including authorised access, notifications without client details, audit trails and tested incident response.
8. Test message delivery, spam handling, bounced messages and outages before stating that submissions are received.

## Incident handling
If confidential information is sent unexpectedly, restrict onward distribution, use approved safeguarding and retention/secure-deletion procedures, record the event privately and escalate to the privacy lead. Do not expose raw submissions to website owners solely by virtue of website-edit permissions.
