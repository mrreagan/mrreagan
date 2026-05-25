# Birthright Roadmap

Prioritized list of remaining work. Updated May 25, 2026.

---

## P1 — Next up

### Documentation tasks (post-dev)
- User will provide a list of documentation tasks AFTER all dev work is
  complete. Test Plan PDF already shipped May 25, 2026
  (`/app/backend/static/exports/birthright-test-plan.pdf`).

---

## P2 — Future

### Advanced Search & Discovery
- Cross-site search across products, workshops, partners, vendors.
- Vendor filters + suggested comparisons.

### `/music` — Curated Playlists
- Mood/activation playlist library (likely external embeds: Spotify/YouTube).

### Email Live Mode
- Flip `EMAIL_DRY_RUN=false` once Resend DNS is verified on `birthright.live`.

### Technical Hardening
- Rate limits on auth + chat WS.
- Redis pub/sub for `ws_manager.py` (horizontal WS scaling).
- Inbound email parsing (reply-to-create-support-request).
- Admin email-resend button on email-log rows.
- Bulk product CSV import.

### Nice-to-haves
- Sponsorship upgrade flow (Amethyst → Ruby etc.).
- Image upload widget on Admin Products (alongside regen).
- Multi-language (en/es).
- Native mobile app.
- Advanced analytics dashboard.

---

## DONE — recent
- Phase 6C.4 (AI Wallet + Research Collaborator + Vendor PDM AI) — May 25, 2026
- Phase 6B.6 (AI Concierge — agentic site-wide guide) — May 25, 2026
- Multi-team Test Plan PDF (11 suites, AI-test-paths included) — May 25, 2026
- Phase 6B.5 (Research moderation queue) — May 25, 2026
- Mobile-menu EXPLORE/FOUNDATION reorganization — May 25, 2026
- v1.11.0 Step 10 (Refund cascade + Agreement v2) — May 25, 2026
- Phase 6C.1/6C.2/6C.3 (DMs, Ombudsman, Disputes) — May 25, 2026
- v1.11.0 Step 9 (Subscription UI parity) — May 25, 2026
- v1.11.0 Step 8.5 (Universal Share & Save) — May 25, 2026
- v1.11.0 Step 8 (Disbursement orchestration) — May 24-25, 2026
