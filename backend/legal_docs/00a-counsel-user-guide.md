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
2. Redline drafts in Word offline (Track Changes on).
3. Email the marked-up files to `legal@birthright.live`.
4. Birthright applies the redlines back into the platform.

Everything below is available if you prefer platform-side work.

---

## 2 · Platform Access

- **URL:** `https://birthright.live`
- **Email:** `counsel@birthright.live`
- **Password:** `counsel-review-2026` (rotate on first login → Account → Security).
- **Role:** `readonly_admin`. Read-only across the admin console; a small
  write allow-list covers comments, redline creation, working-draft
  uploads, and self-service password reset.

A persistent "Counsel review · read-only" banner shows across the
session. Every request from your session is logged to an internal audit
trail (URL, method, response status, IP, user-agent, timestamp); your
account cannot view any log. Full detail is in the Legal Briefing §11
and in the draft **Counsel Terms of Access**.

---

## 3 · Per-Function Options

### 3.1 Read a draft

- **Paper.** Open the paragraph in `LEGAL_BRIEFING_FOR_COUNSEL.docx`
  or the individual draft `.docx` we sent.
- **Platform.** `/counsel` (all drafts) or `/legal/<slug>` for the
  rendered public view.

### 3.2 Propose a change (redline)

- **Paper.** Track Changes in Word, email back to
  `legal@birthright.live`. Birthright transcribes into the platform.
- **Platform.** `/admin/legal/ratifications` → select doc → *Add
  redline* → paste quoted text + suggested replacement + rationale.

### 3.3 See how each redline landed

- **Automated.** You receive a summary email when your roundtrip is
  applied (e.g. _"Terms of Service · 4 accepted, 1 rejected"_).
- **Platform.** Same page as 3.2 → *Roundtrip history*.

### 3.4 Ratify a document

- **Paper.** One-line email:
  > _"We ratify Terms of Service at v1.0 with the redlines applied on
  > [date]."_
  Birthright records the ratification on the platform.
- **Platform.** Ratification write is admin-only by design — counsel
  triggers by email; Birthright records.

### 3.5 Revoke a ratification (rare)

- **Paper.** One-line email with reason. Draft banner returns
  instantly once Birthright records the revoke.

### 3.6 Track what you've reviewed (checklist)

- **Off-platform.** Any matter file works.
- **Platform.** `/admin/counsel-review` — tick each row, initials,
  optional note. Persists indefinitely as the durable sign-off.

### 3.7 Read the change log of ratifications

- **RSS.** `https://birthright.live/api/legal/history.rss` — every
  ratification lands there automatically.
- **Platform.** `/legal/history`.

### 3.8 Your session activity log

By design, counsel cannot view any activity log — including your own.
This protects the audit trail from a compromised session. Birthright
can email a periodic export of your session log to your firm on request.

---

## 4 · Escalation

- **Priority One document blocked > 5 business days.** Email the
  Executive Director at `mr.reagan@gmail.com` for the interim-counsel
  option.
- **Suspected data-protection incident.** Email `security@birthright.live`
  and copy the Executive Director.

---

## 5 · Change Log

| Date | Change |
|---|---|
| 2026-02-04 | v1.0 — initial guide. |
| 2026-02-06 | v1.1 — tightened; Priority One / Priority Two terminology. |
