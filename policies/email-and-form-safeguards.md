# SAMS website email and form controls

**Updated 20 October 2026 — operational setup pending recipient activation**

## Recipient
The intended inbox for non-sensitive organisational enquiries is sam.support.admin@gmail.com.

## Website forms
- Contact, volunteering and partnership forms use FormSubmit to forward messages to the administration inbox.
- Forms collect only name, reply email, and a general topic, area of interest or organisation name. No open narrative message field is offered.
- Users are informed that FormSubmit is an external data processor and must consent before submitting.
- FormSubmit advertises 30-day form submission retention. SAMS's privacy notice discloses this.
- Forms have a hidden spam honeypot field, and FormSubmit's standard anti-spam protections remain enabled.
- A submission redirects to a processing acknowledgement; that page is not proof of inbox delivery.
- FormSubmit requires one test submission followed by confirming the recipient email. Delivery is not considered operational until an actual test is received in the SAMS inbox.
- Forms are intended only for general administrative enquiries. No client intake, health details, case histories or support referrals may be submitted.

## Staff verification emails
- Staff authentication uses Supabase Auth with verified email, password and TOTP second-factor verification compatible with Microsoft Authenticator.
- The Supabase project must be configured with the live SAMS Site URL and staff portal redirect.
- Custom SMTP credentials must be configured in the Supabase Authentication dashboard; no credentials are stored in the public repository.
- Test confirmation and password recovery for an actual authorised account. Until tested, staff email delivery remains unverified.
- Never disable email verification merely to bypass onboarding problems.

## For future secure client support
Use a separate, reviewed client intake workflow with appropriate privacy collection notice, consent, staff case-specific permissions, encrypted storage, monitoring, defined retention and tested backups. Do not forward confidential client records into ordinary Gmail or FormSubmit.

Official FormSubmit documentation: https://formsubmit.co/documentation
Supabase SMTP documentation: https://supabase.com/docs/guides/auth/auth-smtp
