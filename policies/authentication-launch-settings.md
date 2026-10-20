# SAMS production authentication configuration — verified platform limitations
Updated 20 October 2026.

## Database configuration completed
- Supabase free project ID: `evnhavenxnxodymshwwp` (Sydney).
- Row-level security and least privilege for website editing, programs, posts, team tasks and partner contacts.
- Microsoft Authenticator-compatible Supabase TOTP required at AAL2 for all privileged calls.
- Private role helper in `sams_internal` and audit log in private schema.
- Neither visitors nor staff can read or write the confidential client records or form submissions.
- Owner bootstrap checks both SAMS admin mailbox ownership (verified email) and MFA.

## Two provider-managed Auth settings NOT changeable through current Supabase connector
### A. Site URL + redirects
In https://supabase.com/dashboard/project/evnhavenxnxodymshwwp/auth/url-configuration
- Site URL: `https://sams-public-website.onrender.com`
- Additional redirect URL: `https://sams-public-website.onrender.com/portal.html`

Supabase documentation: https://supabase.com/docs/guides/auth/redirect-urls

### B. SMTP
In https://supabase.com/dashboard/project/evnhavenxnxodymshwwp/auth/smtp
- Use an authorised account in a supported transactional email provider or dedicated SMTP account.
- Keep account-confirmation and password-reset verification enabled.
- Do **not** commit SMTP credentials to GitHub, paste them into website content or disable email verification as a workaround.

Supabase's default SMTP delivers **only to organisation-team email addresses**, has strict rates and is not a dependable staff-onboarding service: https://supabase.com/docs/guides/auth/auth-smtp

## General public enquiries
Current public forms explicitly prepare an email draft addressed to `sam.support.admin@gmail.com`; visitors must press Send in their own email app. This is not an automatic form-mail service, and the website must not claim otherwise. Confidential participant details must not enter that mailbox through these public forms.

## Deployment requirements
Once these dashboard settings and verified sender credentials are in place, run an end-to-end acceptance test:
1. Create a staff account from `/portal.html`.
2. Receive confirmation email, open link and return to the correct website.
3. Enrol Microsoft Authenticator and verify a fresh TOTP.
4. Confirm role is initially `pending` and unapproved accounts cannot see internal data.
5. Create/verify the SAMS admin account, attain AAL2 and claim owner role.
6. Owner approves an ordinary worker; worker can see only role-specific operations.
7. Verify password reset, sign-out, rate-limit behaviour, audit event recording.
8. Send one genuine public general enquiry and confirm it reaches the SAMS Gmail inbox (via the visitor's email app for the current pilot).

## Warning
Disabling email verification, accepting unverified owner accounts, exposing a service-role API key, adding permissive client-record policies, or using general tasks for client narratives are **not** acceptable shortcuts.

This is a functional pilot, not an independently certified clinical or confidential case-management system. 
