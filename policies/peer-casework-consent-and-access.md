# SAMS — Peer support case records, consent and referral safeguards

**Operational draft · 20 October 2026**
**Scope: Non-clinical peer support, advocacy, referrals, forms, appointments, client-identified goals and follow-ups.**

## What SAMS will record

SAMS does not act as a medical treatment provider. The work still generates confidential information that may be sensitive or health information under Australian and Victorian law.

For each participant, the minimum relevant record is:
- A reference number and preferred name, plus a safe way to make contact only if needed.
- Who is assigned to the person's case and the role of each assigned worker.
- Whether the person consented to peer-support contact, optional advocacy, a specific referral, or information sharing.
- Dated, factual case notes distinguishing what the participant said, what the worker observed, what action was taken and the next follow-up.
- Goals **chosen with the participant**, including progress and whether the goal was withdrawn.
- Which forms are identified, being completed, submitted, awaiting responses or completed; track form names and statuses rather than storing uploaded identity documents in ordinary email.
- Referrals to existing qualified services, including the recipient and purpose, evidence of specific consent, current status and any agreed follow-up.
- Appointment support: requested or booked service, date, status, confirmation and agreed next step.

## What a peer worker must avoid

Do not diagnose, prescribe, offer detox advice or present peer opinions as clinical assessments. Record only what is needed for support/advocacy. Do not duplicate medical histories, record rumours as facts, or collect identity documents without a specific approved reason.

Case notes should be respectful, factual, date/time stamped and attributed. Do not erase or silently rewrite earlier notes: corrections must be dated and linked to the original. A participant may request that SAMS correct, explain or restrict their information subject to legal obligations.

## Consent and sharing

Explain in clear language: why the information is needed; which people in SAMS can read it; any proposed service to be contacted; what specifically will be shared; how consent can be withdrawn; and practical limits of confidentiality.

Record separately:
- Consent to keep peer-support records.
- Consent to contact the participant by their chosen safe method.
- Consent for a specific referral, with the receiving organisation and purpose.
- Consent for advocacy or sharing details with another service.

A generic signed intake form does not automatically justify sending all case notes to every external service. When consent is withdrawn, stop optional sharing and assess lawful record-retention obligations.

## Staff access and owner authority

Every worker has their own account, a strong password and Microsoft Authenticator. The SAMS owner chooses account type (committee/employee/volunteer/contractor), job role, specific permissions and case assignment.

**Organisation owner status does not mean automatically reading every person's private case notes.** Case-note access will be limited to specifically assigned and authorised peer/support workers. Owners may administer access, incident response and oversight without unrestricted narrative access.

A worker leaving SAMS must have access suspended, sessions revoked, assignments ended and any exported information returned/deleted under a documented exit procedure.

## Safety, oversight and boundaries

SAMS needs documented procedures for suicide risk, overdose, child safety, family violence, complaints, conflicts of interest, mandatory reporting, unsafe contact, staff supervision and vicarious trauma. For immediate danger call 000; refer to relevant qualified crisis and clinical services. Case records should note only the minimum response details necessary.

Track who created, viewed, corrected, exported and shared records in a private audit trail. Never include the confidential narrative itself in generic application logs or notification emails.

## Protection and backup

Do not activate real records without confirmed encryption in transit and at rest, access controls tested against unauthorised workers, **restorable and retained backups**, database activity/incident monitoring, export and deletion procedures, privacy collection notices, secure devices and credential recovery.

SAMS's current free-tier project does **not** provide the guaranteed backup and disaster-recovery arrangements required for safe production client records.

The private data model has been created under `sams_internal` with no anonymous or regular staff API access; the production launch flag is disabled. It is **not an operational confidential CRM yet.**

## Launch decision

Before a real record is entered, SAMS should adopt the procedure, appoint a privacy lead, complete a practical privacy impact assessment for these exact forms and record types, independently verify security and legal obligations, and test backup restoration and an incident tabletop scenario. Activate case-specific policies only after those checks.

Reference information:
- Victorian Health Records Act: https://www.health.vic.gov.au/legislation/health-records-act
- Office of the Australian Information Commissioner: https://www.oaic.gov.au/privacy
