# SAMS website security and release register
**Last updated: 20 October 2026**

## Implemented and published
- Public SAMS site with official provided logo and artwork on Render.
- Supabase project in Sydney free tier, belonging to Substance Affected Mob Support (SAMS) Inc.
- Dynamic public website content, program statuses and announcements.
- Owner and staff dashboard with separate role permissions and Supabase Auth password + TOTP codes compatible with Microsoft Authenticator.
- Staff assignment tasks, partnership directory, account approval flow.
- Row-level security enabled for all SAMS application tables; anonymous access restricted to public pages, published posts and published programs.
- Audit trail for administrative changes, storing no message narratives.
- Browser content security policy for the private portal.
- Confidential case and form-submission tables blocked from anonymous and staff access.
- General contact/volunteer/partnership email composition without automatic transmission.
- Public plain-language privacy notice and support boundaries.

## Not fully verified and must not be represented as production-ready
- Supabase email confirmation redirect allowlist/site URL is not configurable with the current connected tools. End-to-end registration, confirmation and MFA login has not been exercised with a real account.
- Auth email delivery uses Supabase's default provider; no organisation-specific verified SMTP or delivery monitoring is connected.
- A send-on-submit email service to sam.support.admin@gmail.com is not configured. Email drafts require the visitor to send.
- Independent penetration testing, accessibility review and Australian privacy-law sign-off are outstanding.
- A production-grade backup and disaster-recovery plan for sensitive case records is outstanding. Free-tier pause, restoration and limits require monitoring.
- Full confidential client CRM workflows are intentionally disabled.

## Release rule
Do not enable confidential intake/case files until lawful collection, consent, clinical versus peer boundaries, child-safety and duty-of-care escalation, appropriate staff training, MFA, security testing, encrypted storage, backup restoration tests, notifications, retention and breach response have been signed off.

## Owner verification
SAMS's verified administration email (sam.support.admin@gmail.com) may claim the first owner role only after authentication reaches Supabase's MFA assurance level AAL2. Role changes and internal workflows require AAL2 as enforced by the database.

## Current contacts
General enquiries: sam.support.admin@gmail.com (non-sensitive only).
Emergency: 000. 13YARN: 13 92 76. Victorian DirectLine: 1800 888 236.
