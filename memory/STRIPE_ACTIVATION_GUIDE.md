# Stripe Activation Guide for birthright.live

This is the **exact step-by-step** to take Stripe from TEST mode to LIVE
mode and to enable Stripe Connect payouts for artist partners.

Current state (as of this writing):
- `STRIPE_API_KEY` in `/app/backend/.env` is a **TEST key** (`sk_test_...`).
- No webhook secrets are configured (`STRIPE_WEBHOOK_SECRET`,
  `STRIPE_CONNECT_WEBHOOK_SECRET` are unset → signature verification is
  effectively disabled).
- Stripe Connect (artist payouts) code is fully wired but inactive until
  a Connect platform is enabled in your Stripe dashboard.

The whole flip-the-switch process takes ~30–45 minutes once your Stripe
account is approved for live mode.

---

## Part A — Activate your Stripe account for live charges

1. Sign in at **https://dashboard.stripe.com**.
2. Top-right toggle: switch from **Test mode** → **Live mode**.
   - If you see "Activate payments" instead, click it and finish the
     activation form (legal entity, bank account, business address, EIN/SSN,
     statement descriptor "BIRTHRIGHT"). Approval is usually < 24h.
3. Once live mode is enabled, the dashboard header turns from orange
   (test) to plain.

---

## Part B — Grab the LIVE secret key

1. In live mode, go to **Developers → API keys**.
2. Under "Standard keys", click **Reveal live key** on **Secret key**.
3. Copy the `sk_live_...` value. **Do not paste it into chat or commit
   it anywhere.**
4. Send it to me here when ready — I'll drop it into
   `/app/backend/.env` as `STRIPE_API_KEY` and restart the backend.

(The publishable key `pk_live_...` is not needed — checkout sessions are
created server-side and the frontend just opens the returned URL.)

---

## Part C — Configure the Checkout webhook (mandatory)

This is the webhook that confirms purchases (course enrollment, merch
orders, subscriptions) once Stripe finalizes payment.

1. Live mode dashboard → **Developers → Webhooks → Add endpoint**.
2. **Endpoint URL:** `https://birthright.live/api/webhook/stripe`
3. **Events to send:** click "Select events" and check at minimum:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
   - `checkout.session.async_payment_failed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`
4. Click **Add endpoint**, then on the endpoint detail page click
   **Reveal signing secret** and copy the `whsec_...` value.
5. Send me that `whsec_...` — I'll set it as `STRIPE_WEBHOOK_SECRET` in
   `/app/backend/.env`.

---

## Part D — Enable Stripe Connect for artist payouts

This lets every approved artist partner connect their own bank account
and receive their share of sales automatically.

1. Live mode dashboard → top-left search → "Connect" → click **Get
   started with Connect**.
2. Choose **Platform or marketplace** as your business model.
3. Pick the **Express** account type (Stripe-hosted onboarding — the
   onboarding link we already generate uses this).
4. Branding tab → set:
   - Platform name: **birthright**
   - Color: `#1a1a1a` (or your hex of choice)
   - Logo: upload a square 512×512 PNG of the b-mark.
5. Settings → "Capabilities" → ensure **`transfers`** is enabled (it is
   by default for Express).
6. **Add a second webhook** specifically for Connect events:
   - **Endpoint URL:** `https://birthright.live/api/webhook/stripe-connect`
   - **Events to listen to:** select "Account" → check:
     - `account.updated`
     - `account.application.authorized`
     - `account.application.deauthorized`
     - `capability.updated`
   - **Listen to:** "Events on Connected accounts" (this is the
     critical checkbox — without it the webhook never fires for partner
     accounts).
7. Copy the new `whsec_...` signing secret.
8. Send me that value — I'll set it as
   `STRIPE_CONNECT_WEBHOOK_SECRET` in `/app/backend/.env`.

---

## Part E — Verify the live flow (we do this together)

Once Parts A–D are done and I've applied the three secrets:

1. I restart backend (`sudo supervisorctl restart backend`).
2. Smoke test: `curl https://birthright.live/api/products?type=merch`
   returns the catalog (no Stripe needed yet).
3. **Real $1 charge test** — I'll create a $1 test product and walk one
   purchase end-to-end with a real card. Stripe takes its standard fee
   (~$0.33); you can refund the $0.67 net immediately from the dashboard.
   This confirms:
   - Checkout session creation works against live keys.
   - Webhook signature verifies and the order is marked `paid`.
   - The buyer receives the Resend confirmation email (once DKIM verifies
     — see DNS step below).
4. **Connect onboarding test** — `demo@birthright.org` artist account
   clicks "Connect Stripe" → completes Express onboarding with a real
   bank account (or Stripe's test bank routing 110000000 / 000123456789
   if your account allows live test-Connect) → `account.updated` webhook
   fires → status flips to `ready` in `/dashboard/artist`.
5. **Test transfer** — once an artist is `ready`, I issue a $1 manual
   transfer through `POST /api/artist/payout/process` and verify it
   appears in their Stripe Express dashboard.

After step 5 passes, Stripe is live.

---

## Part F — Optional but recommended

- **Statement descriptor:** Stripe → Settings → Public details →
  Shortened descriptor: `BIRTHRIGHT` (max 22 chars).
- **Tax:** Stripe → Tax → enable automatic sales-tax collection for the
  US states you have nexus in. The checkout router already supports
  this once you toggle it on in the dashboard — no code change.
- **Radar (fraud):** leave on default rules to start; revisit after the
  first 30 days of live volume.
- **Apple Pay domain verification:** Stripe → Settings → Payment methods
  → Apple Pay → "Add new domain" → `birthright.live` → upload the file
  Stripe gives you to `/.well-known/apple-developer-merchantid-domain-association`
  (ping me and I'll wire that static file in).

---

## What I need from you (summary)

Three secrets, one at a time or all together:

1. `STRIPE_API_KEY` — `sk_live_...` from Part B.
2. `STRIPE_WEBHOOK_SECRET` — `whsec_...` from Part C step 5.
3. `STRIPE_CONNECT_WEBHOOK_SECRET` — `whsec_...` from Part D step 7.

The moment all three are set and the backend restarted, the platform is
operating on real money. I'll then run the verification flow in Part E
with you watching.
