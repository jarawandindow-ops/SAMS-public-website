# SAMS free-access owner portal and public site

**Current release:** $0 pilot. Public organisation content can be edited from the owner dashboard; staff have individual password + six-digit authenticator sign-in. Supabase PostgreSQL is needed for persistence and Render free Python web hosting can run the app. The live site is **not yet deployed** until the database and private credentials are configured. There are no passwords or secrets in this repository.

**Safety gate:** `APP_ENV=pilot` always disables case records and all enquiry submissions regardless of what other flags say. Never enter real client, health, substance use or family records into this pilot. Independent privacy, backup and penetration testing are still required for eventual real case management.

**Authenticator details:** This uses standards-based TOTP codes in the Microsoft Authenticator app under **Other account**, not Microsoft Entra tenant authentication or Microsoft push sign-in. Microsoft 365 is not required.

See `DEPLOY-FREE.md` and `.env.pilot.example` for deployment.

SAMS branded site image assets from SAMS-provided visual identity. © SAMS artwork supplied by organisation.
