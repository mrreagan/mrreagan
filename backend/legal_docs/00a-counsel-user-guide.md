# Counsel User Guide

_Birthright Foundation · February 2026 · birthright.live_

A quick-reference for outside counsel working with Birthright's platform.
Every function has a **paper path** (email + `.docx`) and a **platform
path**. Use whichever fits your workflow.

Contact: `legal@birthright.live`.

---

## 1 · The Short Version

You do not need to sign in to the platform for a normal review pass.

1. Download `LEGAL_BRIEFING_FOR_COUNSEL.docx` and this guide.
2. Comment on drafts in Word offline.
3. Email the marked-up files to `legal@birthright.live`.
4. Birthright applies the comments back into the platform.

Everything below is available if you prefer platform-side work.

_Note: the inline **redline** workflow (track-changes export / import
round-trip on the platform) is temporarily disabled while it is
being simplified. Comments are fully live; redlines can be handled by
email `.docx` in the interim._

---

## 2 · Platform Access

- **URL:** `https://birthright.live`
- **Email:** `counsel@birthright.live`
- **Password:** `counsel-review-2026` (rotate on first login → Account → Security).
- **Role:** `readonly_admin`. Read-only across the admin console; a small
  write allow-list covers comments, working-draft uploads, and
  self-service password reset.

A persistent "Counsel review · read-only" banner shows across the
session. Every request from your session is logged to an internal audit
trail (URL, method, response status, IP, user-agent, timestamp); your
account cannot view any log. Full detail is in the Legal Briefing §11
and in the draft **Counsel Terms of Access**.

---

## 3 · The Counsel Dashboard

`/counsel` (Counsel Dashboard) is the single workspace for the review.
It contains, in one page:

- The full draft library, grouped by category and filterable by Priority
  One / Priority Two.
- The Ratification & Redline Console link (top-right nav) for the
  fine-grained ratification / rollback / release workflow.
- Your session activity log link (also top-right nav).
- The "What triggers an email" note (see §5 below).
- The **Review Checklist** — auto-marks each doc you've opened from the
  activity log; manual sign-off toggle per doc. (This used to live at
  `/admin/counsel-review` — it is now merged into the Dashboard so you
  work from a single page.)

---

## 4 · Per-Function Options

### 4.1 Read a draft

- **Paper.** Open the paragraph in `LEGAL_BRIEFING_FOR_COUNSEL.docx`
  or the individual draft `.docx` we sent.
- **Platform.** `/counsel` (all drafts) or `/legal/<slug>` for the
  rendered public view.

### 4.2 Propose a change

- **Paper.** Add margin comments in Word, email back to
  `legal@birthright.live`. Birthright applies the changes.
- **Platform.** `/admin/legal/ratifications` → select doc → add a
  comment on the section. (Redlines are temporarily disabled — post as
  a comment or send by email.)

### 4.3 See how a comment landed

- **Automated.** You receive a summary email when your comments are
  reviewed and applied.
- **Platform.** Same page as 4.2 → the comment thread + the ratification
  history.

### 4.4 Ratify a document

- **Paper.** One-line email:
  > _"We ratify Terms of Service at v1.0 with the changes applied on
  > [date]."_
  Birthright records the ratification on the platform.
- **Platform.** Ratification write is admin-only by design — counsel
  triggers by email; Birthright records.

### 4.5 Revoke a ratification (rare)

- **Paper.** One-line email with reason. Draft banner returns instantly
  once Birthright records the revoke.

### 4.6 Track what you've reviewed (checklist)

- **Platform.** `/counsel` → the Review Checklist section auto-ticks
  each doc that shows up in your activity log (a download, an open,
  or a comment post all count). Manual sign-off toggle per doc for the
  durable record.

### 4.7 Change log of ratifications

- **RSS.** `https://birthright.live/api/legal/history.rss` — every
  ratification lands there automatically.
- **Platform.** `/legal/history`.

### 4.8 Your session activity log

By design, counsel cannot view any activity log — including your own.
This protects the audit trail from a compromised session. Birthright
can email a periodic export of your session log to your firm on request.

---

## 5 · What Triggers an Email

Every one of these fires automatically — no manual step needed.

| Event | Recipient | When |
|---|---|---|
| Counsel clicks **Mark ready for admin review** on a working draft | All admins | Inline at click time |
| Someone @-mentions `@admin` or `@counsel` in a comment | That role | Real-time (if opted in) or daily digest at 08:00 UTC |
| Admin **Releases** a working draft | Subscribed partners + members | Inline at release |
| Admin **Rolls back** to a prior version | Subscribed partners + members | Inline at rollback |
| Redline round-trip `.docx` applied by admin (when re-enabled) | Counsel | Inline, per-decision summary |

**What does NOT send email**: document downloads, individual comment
posts (they roll up into the digest), version-history views, opening
the Diff modal, opening the Counsel Dashboard.

**No manual steps** are needed to trigger any of the above. To change
your @mention delivery cadence (real-time vs daily digest), use the
toggle on the Counsel Dashboard.

---

## 6 · Escalation

- **Priority One document blocked > 5 business days.** Email the
  Executive Director at `mr.reagan@gmail.com` for the interim-counsel
  option.
- **Suspected data-protection incident.** Email `security@birthright.live`
  and copy the Executive Director.

---

## 7 · Change Log

| Date | Change |
|---|---|
| 2026-02-04 | v1.0 — initial guide. |
| 2026-02-06 | v1.1 — tightened; Priority One / Priority Two terminology. |
| 2026-02-06 | v1.2 — renamed "Counsel Console" → "Counsel Dashboard"; merged the standalone Review Checklist into the Dashboard; documented email triggers; redline workflow paused. |
