# Cloudflare + Resend Setup for Counsel Email

**Effective date:** February 2026 · Owner: Executive Director
(admin@birthright.live).

You need to do these once, per production domain, before onboarding
your first real outside counsel. **You do not need code changes** — this
is all DNS and dashboard config.

---

## Step 1 · Verify `birthright.live` in Resend (10 min)

So Birthright's automated emails (`Roundtrip applied …`,
`Set your counsel password`, `You accepted agreement v…`) send from a
recognised sender and do not hit spam.

1. Sign in to Resend at https://resend.com/domains.
2. Click **Add domain**, enter `birthright.live`.
3. Resend gives you **six DNS records** — three MX, one SPF (TXT),
   one DKIM (CNAME), one DMARC (TXT).
4. In Cloudflare, go to **DNS → Records**. Paste each record exactly
   as Resend shows it. (Cloudflare has a "Resend" template that
   auto-adds them — use it if visible.)
5. Wait ≤ 10 min. Resend's dashboard should flip the domain to
   **Verified** ✅ on the next check.

**Verify it worked:**
```
$ dig +short TXT birthright.live         # should contain "v=spf1 include:_spf.resend.com ~all"
$ dig +short TXT _dmarc.birthright.live  # should exist
```

Or open the Resend dashboard — a green ticks means done.

---

## Step 2 · Cloudflare Email Routing → counsel's firm inbox (5 min)

Give counsel an address at `birthright.live` that forwards to their
firm inbox, so their real email address stays out of Birthright's
audit logs.

1. Cloudflare dashboard → your `birthright.live` zone → **Email →
   Email Routing**.
2. If not enabled, click **Enable Email Routing** and accept the DNS
   changes Cloudflare proposes (they add MX records; safe alongside
   the Resend MX records because Resend uses different subdomains).
3. **Destination addresses**: click **Add destination** and enter
   counsel's real firm email (e.g., `jane.smith@example-law.com`).
   Cloudflare sends counsel a confirmation email — they must click
   through once.
4. **Routing rules**: click **Create address** and route
   `counsel@birthright.live` → the destination you just added.
5. Send a test email to `counsel@birthright.live` from your personal
   Gmail — it should hit counsel's firm inbox in ≤ 30 s.

---

### Step 3 · (Optional) rotate to a routed alias

If you'd prefer counsel to login under a routed alias — e.g. an alias
scoped to a particular firm engagement — change the stored email:

1. Sign in as admin at https://birthright.live/login.
2. Go to **Admin → Governance & System → Counsel credentials**.
3. Change the email to your preferred routed alias (e.g. `counsel-jane@birthright.live`).
4. Click **Rotate credentials**.

The default `counsel@birthright.live` continues to work if you don't
rotate; this step is only needed when you want a distinct alias per
engagement.

---

## Step 4 · Send counsel their set-password link (1 min)

1. On the same **Counsel credentials** page, click **Send
   set-password link**.
2. The link lands at `counsel@birthright.live`, which Cloudflare
   forwards to counsel's firm inbox.
3. Counsel clicks it, sets their own 12-character password, and
   signs in at `/login`.

Admin never sees the plaintext password. The link is one-time and
expires in 24 hours. Any active counsel JWT is automatically revoked
the moment they submit the new password, so no stale session
lingers.

---

## Optional · SPF alignment for outbound Cloudflare routing

Cloudflare Email Routing only inbound-forwards. If you also want to
*send* email from `counsel@birthright.live` (rare — Birthright's
system emails send from `hello@birthright.live`, and counsel replies
go to their firm inbox via the forward), configure Cloudflare's
outbound-alias feature or add a second Resend domain for the counsel
alias. Not required for the current setup.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Set-password email lands in spam | Verify Resend DKIM (Step 1). If green in Resend, wait 24 h for reputation to warm up. |
| Counsel says "your link says invalid" | Resend it — links are one-time. Older link is auto-superseded when you send a new one. |
| Cloudflare routing test email never arrives | Confirm counsel clicked the destination-address confirmation email. Cloudflare will not forward until the destination is verified. |
| Login shows "Session revoked" | Expected right after a rotate. Counsel signs in with the new password. |
| `dig` shows old TXT records | DNS propagation can take up to 24 h on some resolvers. Use `dig @1.1.1.1 …` to query Cloudflare directly. |

---

## What DOES NOT need to change

- `backend/.env` — DB is source of truth after first seed; env values
  are only used to bootstrap a fresh install.
- `PUBLIC_SITE_URL` env var — optional; set to `https://birthright.live`
  if you want set-password links to render that host even when the
  request arrives with a different host header. Otherwise the link
  uses the request host, which is fine on `birthright.live`.
- Frontend build — no code changes needed. Just redeploy if the
  `PUBLIC_SITE_URL` env change matters to you.

---

*Questions? admin@birthright.live.*
