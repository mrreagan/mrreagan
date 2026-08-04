> **COUNSEL USER GUIDE — READ FIRST (v1 · Feb 2026)**
>
> Standalone instructions for Birthright Foundation's outside counsel.
> Also embedded near the front of the Legal Briefing for one-stop
> reference.
>
> **The whole point of this guide is to keep your billable time low.**
> For every function you might do on our platform, this guide names
> a *Fast Path (paper / email)* — the cheapest option — first, and a
> *Platform Path* second in case you prefer it. Wherever the platform
> path costs meaningful minutes, we've marked it **"push to admin"**:
> hand it back to Birthright's Executive Director and skip the clicks.
>
> Contact: legal@birthright.live · overwhelm@birthright.live never gets
> read; use `legal@` for everything.

# Counsel User Guide

## 0. Bottom Line
> **Cheapest workflow for you:**
> 1. Download the two `.docx` files.
> 2. Redline them in Word offline. Use track changes.
> 3. Email the marked-up files to `legal@birthright.live`.
> 4. We do all the platform clicks.
>
> You never have to log into the platform for a normal review pass.
> Everything below is optional.

## 1. What You Should Actually Download
Ask Birthright to email you these two files (they will, on request):

| File                                     | What it is                                |
|------------------------------------------|-------------------------------------------|
| `LEGAL_BRIEFING_FOR_COUNSEL.docx`        | All 22 drafts + business context, in one Word file |
| `00a-counsel-user-guide.docx` (this doc) | You're reading it                         |

That is enough for a paper review. Everything else in this guide is
"optional extras" for counsel who *want* live-platform access.

## 2. Your Platform Credentials (Optional)
Only relevant if you want to browse the site itself. Skip this section
if you're happy with paper.

- **URL:** https://birthright.live *(preview URL sent separately for
  pre-launch review sessions)*
- **Email:** counsel@birthright.org
- **Password:** counsel-review-2026 *(change on first login → Account → Security)*
- **Role:** `readonly_admin` — read-only across the whole admin console;
  a small allow-list lets you post comments and reset your own password.

Every page shows an amber "You are signed in as counsel (read-only)"
banner. That's expected, not an error.

## 3. Per-Function Fast Paths

For every task in a review cycle, here is the cheapest way to do it —
and where we recommend you push work back to Birthright's admin.

### 3.1 Read a legal document
- **Fast path** — Open the paragraph in the `LEGAL_BRIEFING_FOR_COUNSEL.docx`
  file we sent you. Every draft is embedded in that briefing with its
  section headings intact. Total cost: **0 platform minutes.**
- **Platform path** — Visit `/legal/<slug>` (Terms, Privacy, Cookie
  Notice, Refunds, Scholarships, Community Standards) for the
  rendered public view.
- **Push to admin** — Not applicable; reading is free either way.

### 3.2 Propose a change (redline)
- **Fast path** — Turn on Track Changes in Word (Review → Track
  Changes → For Everyone). Redline the paragraph. Save. Email the
  file back to `legal@birthright.live`. Total cost: **your usual
  redlining minutes**, no platform time added.
- **Platform path** — Sign in, open `/admin/legal/ratifications`,
  select the doc, click *Add redline*, paste the quoted text and
  suggested replacement, add your rationale, submit. Roughly
  **3–5 min per redline** on the platform.
- **Push to admin** — Just email the marked-up doc. **The admin will
  transcribe each redline into the platform for you.** They do this
  in ~30 seconds per redline; you avoid a per-redline typing surcharge.

### 3.3 See counsel-briefing bundle regenerate after redlines are applied
- **Fast path** — You don't do this. The site rebuilds the bundle
  automatically after admin applies your roundtrip and emails you the
  fresh `LEGAL_BRIEFING_FOR_COUNSEL.docx` on request. Cost: **0
  platform minutes.**
- **Platform path** — Not available to you (write-locked; admin only).
- **Push to admin** — Fully already there.

### 3.4 See how each of your redlines landed
- **Fast path** — You will receive an **automated summary email** the
  moment your roundtrip is applied. Subject reads e.g. *"Roundtrip
  applied · Terms of Service · 4 accepted, 1 rejected."* The body
  itemises accepted, rejected, and skipped counts. Cost: **0
  platform minutes** — the email arrives at your inbox.
- **Platform path** — Sign in, open `/admin/legal/ratifications`,
  select the doc, scroll to *Roundtrip history* to see every
  application with counts and timestamps.
- **Push to admin** — Ask the admin to CC you on any manual
  application decisions if you want narrative context; otherwise the
  automated email is enough.

### 3.5 Ratify a document (the moment of formal sign-off)
- **Fast path** — Send a one-line email:
  > *"We ratify Terms of Service at v1.0 with the redlines you
  > applied on \[date]. — \[Firm]."*
  That email is your ratification of record. Cost: **1 min.**
- **Platform path** — Not available to you (write-locked; admin only).
- **Push to admin** — Admin marks the ratification on
  `/admin/legal/ratifications`, entering your firm name, the date,
  and a link to your email. The public draft banner turns off
  automatically and a change-log entry appears at `/legal/history`
  (also on RSS for anyone subscribed).

### 3.6 Revoke a ratification (rare — e.g., a mandatory law change)
- **Fast path** — Email `legal@birthright.live` with a one-line reason.
  Cost: **1 min.**
- **Platform path** — Not available to you.
- **Push to admin** — Admin clicks *Revoke ratification*; the draft
  banner returns instantly.

### 3.7 Track what you've reviewed (checklist)
- **Fast path** — Track internally in your firm's matter file. Cost:
  **0 platform minutes.**
- **Platform path** — Sign in, open `/admin/legal-docs`, tick each
  row's checklist and enter your initials. ~10 seconds per row.
- **Push to admin** — When you email that you've completed a set,
  the admin will tick the boxes for you and note "counsel confirmed
  via email \[date]." You never touch the platform.

### 3.8 View activity log of your own account
- **You cannot see this by design.** Only full admins can view
  `/admin/counsel-activity`. This is a bilateral protection — it
  shows Birthright that only accounts you sanctioned accessed the
  material, and it protects Birthright against a hostile actor
  tampering with the log.
- **Push to admin** — Ask the admin to email you a monthly digest of
  your session's access log if your firm wants it for its file.

### 3.9 Read the change-log of what has been ratified
- **Fast path** — Subscribe to the public RSS feed at
  `https://birthright.live/api/legal/history.rss`. Every ratification
  lands there automatically. Cost: **once to set up your feed reader.**
- **Platform path** — Visit `/legal/history`.
- **Push to admin** — Not needed; both are free.

## 4. What Only YOU Should Do (Do Not Push to Admin)
These functions cost billable time no matter what, and should be
done by counsel personally to keep the professional record clean:

- The **substantive legal analysis** on the drafts.
- The **rewording of any redline** whose new text you propose.
- The final **email of ratification** for each document.
- Any advice on **licensing, insurance, or dispute-jurisdiction**
  choices flagged in the drafts.

Everything else in this guide can be pushed to admin.

## 5. Emergency & Escalation
- Ratifying counsel unavailable for > 5 business days on an
  Essential Section A document? Email
  `james@birthright.live` (Executive Director) to trigger the
  interim-counsel option.
- Suspected data-protection incident? Email
  `security@birthright.live` and phone the ED.

## 6. Change Log for This Guide
| Date       | Change                                                             |
|------------|--------------------------------------------------------------------|
| 2026-02-04 | v1.0 — initial counsel guide, per-function billable-time fast paths |

---

*This guide itself is a first draft. Suggestions welcome via
`legal@birthright.live`.*
