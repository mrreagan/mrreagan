# Birthright Foundation Platform — PRD

## Original Problem Statement
React + FastAPI + MongoDB platform for the Birthright Foundation — attachment-theory research, artist gallery, partner economy, AI-powered patron experiences, and merch.

## Persona
- **Founder/Operator** — governance, payouts, content, dashboards.
- **Artists** — gallery partnership, patronage payouts, tiered referral economics.
- **Partners** (Vendors / Stewards / Researchers / Community) — Partner Economy modules.
- **Members** — research, events, merch.

## Core Brand Aesthetic
- Cream `#F8F2E5` + brand teal `#2C4E5A` + gold `#A87A4A`
- Cormorant Garamond italic + bold-upright roman focal word
- Generous whitespace, gold hairline rules, sacred-but-secular tone

## What's Been Implemented (recent — Feb 2026)
### Iter 66 — Working-Draft Inline Comments (Feb 05 2026)
- **New collection `legal_working_draft_comments`** — threaded comments scoped to a specific `working_draft_id`. Anchor to a specific line (`line_number` + `side`) or leave as general note.
- **Backend endpoints**: `GET /api/legal/working-drafts/{slug}/comments` (list, sorted asc by created_at), `POST /api/legal/working-drafts/{slug}/comments` (create + reply, 4KB body cap, side validation, parent must belong to same WD), `POST .../comments/{id}/resolve` (toggle resolve/unresolve, either party), `DELETE .../comments/{id}` (admin any / counsel own; recursive cascade to ALL descendants, not just depth-1). `GET /working-drafts` now includes per-row `comment_stats: {total, open}` via a single aggregate.
- **Frontend DiffModal** loads comments alongside the working draft. Side-by-side rows expose a `+` hover button on the working-column line number → inline compose form appears as a sibling `<tr>` under that row. Existing comments render inline as thread cards immediately after their anchor line. Reply / Resolve / Reopen / Delete controls inline (delete only for author or admin). General comments panel below the diff for un-anchored notes.
- **Row badge**: `/counsel` rows show `N open · M total` comment count (color-shifts to green when all resolved). Diff modal header shows the same count.
- **Testing**: `testing_agent` iter 50 caught two CRITICAL frontend bugs: (a) compose form leaked on removed-only rows because `composeLine === row.rightNum` matched null===null → fixed with `composeLine != null` gate; (b) `<CommentCard/>` self-recursion crashed the visual-edits babel plugin → resolved by aliasing `const NestedCard = CommentCard;` inside the recursive branch. Backend cascade delete extended to any depth (verified 3-deep thread returns `deleted: 3`). All 36 backend pytest cases pass; all comment flows work end-to-end.

### Iter 65 — Release History Timeline + Admin Rollback (Feb 05 2026)
- **Content snapshots on release**: `release_working_draft` now persists `content_md_snapshot` and `change_summary` on the ratification row. Enables true rollback.
- **New endpoint `GET /api/legal/history-timeline/{slug}?limit=5`**: returns `{total_versions, current_version, current_body_hash, versions:[…]}`. Each version carries `change_summary` (edits, authors, action counts, first/last edit timestamps) + `can_rollback` flag. `limit` validated via `Query(ge=1, le=50)` → 422 on 0 or garbage. Ordering is deterministic (`ratified_at` DESC then `id` DESC). Snapshot-existence scan bounded to the current page ids, not the full slug history.
- **New endpoint `POST /api/legal/history/{slug}/rollback/{ratification_id}`**: admin-only. Restores the target snapshot as a NEW ratification (auto-bumps minor version), rebuilds the DOCX bundle, and auto-discards any open working draft with a proper change_log audit entry so the discard reason isn't lost.
- **Frontend History modal** on `/counsel` — click `History` on any row → modal shows total count + version cards for the last 5 releases (Show more paginates by 5). Each card renders version, localised date, ratified_by, notes, change summary chip (`5 edits by counsel@ · 2 upload full, 3 apply roundtrip`), Rollback badge if applicable, `Current` badge on the newest. Rollback button admin-only.
- **Testing**: `testing_agent` iter 49 — 16/16 backend + 100% frontend. All optional defensive suggestions implemented (Query validators, deterministic ordering, bounded ID scan, human-readable date in rollback notes, WD change_log entry on rollback discard, ratification-id data attribute for testid collisions).

### Iter 64 — Diff View + Admin Auto-Notify (Feb 05 2026)
- **Side-by-side redline modal** on `/counsel` — click `View diff` on any row with a working draft to see a two-column diff (released vs working) with green/red line highlights and line numbers. Toggle to unified/git-style view. Admins get a `Release from here` shortcut in the diff footer that jumps into the release modal.
- **Empty-state**: when the working draft is byte-identical to the released version, the diff modal shows "Working draft is identical to the released version" instead of dumping the entire doc as context.
- **Admin email notification** on `POST /working-drafts/{slug}/mark-ready` — emails every user with `role=admin` via Resend (template `legal_working_draft_ready`). Response returns `email_scheduled: true|false`.
- **Idempotent**: calling mark-ready on an already `awaiting_admin` draft returns `email_scheduled: false` — no duplicate admin spam.
- **Background dispatch**: mark-ready uses FastAPI `BackgroundTasks` so the UI response isn't held up by the Resend round-trip.
- **z-index fixes**: raised both modals to `z-[60]` so the persistent cookie-consent banner (z-50) no longer intercepts clicks on Close/Release buttons.
- **New dep**: `diff@9.0.0` (jsdiff) for line-diff computation.
- **Testing**: `testing_agent` iter 48 — 11/11 backend + 10/10 frontend after fixes. Real Resend delivery confirmed via email_log entry with `template=legal_working_draft_ready`.

### Iter 63 — Counsel Console + Working-Draft workflow (Feb 05 2026)
- **New `/counsel` page** (`CounselConsole.jsx`) — filtered admin console visible via a "Counsel Console" shortcut in both admin AND counsel user-menu dropdowns.
- **New collection `legal_doc_working_drafts`** — every counsel/admin upload lands here as a WORKING VERSION. The public source `.md` is untouched until admin explicitly releases the working draft.
- **New endpoints**: `GET /api/legal/working-drafts`, `GET /api/legal/working-drafts/{slug}`, `GET /api/legal/working-drafts/{slug}/download` (returns `.docx` for offline edit), `POST .../mark-ready`, `POST .../release` (admin only — auto-bumps minor version with modal override), `POST .../discard` (admin only).
- **Rewired flows**: `POST /api/legal/docs/{slug}/upload` and `POST /api/legal/comments/{slug}/apply-roundtrip` now write to the working draft instead of the released `.md`. Public site stability is preserved during counsel iteration.
- **Release flow**: writes working-draft `content_md` → `.md`, calls `_run_docx_rebuild` (which also appends EU/UK compliance addendum), then hashes the FINAL on-disk content for the ratification body_hash (fixes the "still shows unratified" bug flagged by testing_agent). Auto-creates the next ratification version, marks working-draft state=released.
- **Permissions**: `readonly_admin` (counsel) can create/edit/mark-ready/upload/download. Admin can also release + discard. `POST .../release` and `.../discard` re-guard with in-body `user.role != 'admin'` → 403.
- **UX polish**: file input value reset after upload (so re-selecting same file re-fires change), header layout stacks (back link → label → h1 no longer collide), release modal pre-fills the auto-bumped version and accepts admin override.
- **Testing**: `testing_agent` iter 47 — 17/17 backend pytest cases pass, 100% of frontend flows pass, HIGH hash-order bug caught & fixed, empty-body 422 caught & fixed, cosmetic header + input-reset issues caught & fixed.

### Iter 62 — Counsel scoped access + full-notice uploads + eye-icon restore (Feb 05 2026)
- **Middleware refactor** (`/app/backend/utils/readonly_admin.py`): `ReadonlyEnforcementMiddleware` no longer default-denies every counsel mutation. It now only fences `/api/admin/*` mutating methods, with a narrow allow-list for `/api/admin/legal/*` and `/api/admin/settings/counsel/set-password[-from-token]`. Counsel can now shop, check out, edit their profile, DM, post reviews, and author their full legal-review workflow (comments, redlines, roundtrips, uploads).
- **New endpoint `POST /api/legal/docs/{source_slug}/upload`**: counsel or admin can upload a full replacement for any legal source doc as `.md`, `.markdown`, `.txt`, or `.docx`. `.docx` is converted to Markdown via `python-docx` (heading levels 1-6, paragraphs, list items; tables/images flagged in an HTML comment). Auto-rebuilds the DOCX bundle and audits `legal.doc.upload_replacement`. Any existing ratification stops matching because the body hash changes — banner returns until re-ratified.
- **Frontend "Replace entire notice" card** on `/admin/legal/ratifications` — visible to both admin and counsel, wraps a hidden file input with `accept=".md,.markdown,.txt,.docx"`. Confirm dialog before upload.
- **View-password eye toggle restored** on `Login.jsx`, `Register.jsx`, `ResetPassword.jsx`, `CounselSetPasswordPage.jsx` (2 fields), `AdminCounselSettings.jsx` (2 fields), `PartnerInvite.jsx`, `FeaturedInvite.jsx`. Uses `lucide-react` `Eye`/`EyeOff` icons. Each toggle has a unique `data-testid`.
- **Domain sweep**: `scripts/build_test_plan.py` seed CREDS + `routers/partner_prospects.py` + `STRIPE_ACTIVATION_GUIDE.md` all migrated from `@birthright.org` → `@birthright.live`. Historical CHANGELOG entries left as-is.
- **Counsel banner reworded** (`ReadOnlyBanner.jsx`) to reflect the new scoped-access model rather than the old fully-read-only claim.
- **Testing**: `test_iter46_counsel_upload.py` — 13/13 backend + 7/7 frontend flows pass.

### Iter 61 — Public Legal Renderer (Feb 04 2026)
- New backend routes `GET /api/legal/pages` (list) and `GET /api/legal/pages/{slug}` (render). Slugs are allowlisted to `terms`, `privacy`, `cookie-notice`, `refunds`, `scholarships`, `community-standards`.
- Markdown is rendered server-side with `markdown==3.10.3` (extra, tables, sane_lists, toc). The leading AI-first-draft blockquote is stripped and re-surfaced as an amber "Draft — pending counsel review" banner in the UI, keeping the actual body clean.
- New frontend route `/legal/:slug` → `LegalDocPage.jsx` with editorial `.legal-prose` typography, last-updated stamp, .docx download link, and unknown-slug redirect to `/`.
- `CookieConsentBanner` now links to `/legal/cookie-notice` (was `/legal/cookies`).

### Iter 60 — Checkout consent + AI-caption alt-tag wiring (Feb 04 2026)
- **Cart consent gate**: `Cart.jsx` now shows a "Before you check out" block with two mandatory tick-boxes (Terms of Service + Privacy Policy), each linking to `/legal/terms` and `/legal/privacy`. Checkout button stays disabled until both are checked. Matches the `/register` gate for consistency.
- **AI-caption alt tags**: `<img>` tags across the storefront now prefer `image_caption` (the AI vision output) for accessibility and SEO — `Cart` items, `ProductDetail` hero, `PartnerProfilePage` avatar, `PartnersDirectory` cards, `Research` covers, `PartnerOfferings` tiles, `GlobalSearch` result thumbs.
- **`routers/search.py`**: search API now returns `image_alt` for every result type (product / partner / workshop / research / gallery) and the frontend consumes it in `GlobalSearch`.

### Iter 59 — Sponsor Pill + Campaigns system (Feb 2026)
- **New backend router**: `routers/campaigns.py` with public list/detail/pledge endpoints (`GET /api/campaigns`, `GET /api/campaigns/{slug}`, `POST /api/campaigns/{slug}/pledge`) and admin CRUD + pledge status management. Every API response embeds a `non_deductible_notice` string so the frontend cannot forget to display it.
- **New DB collections**: `sponsor_campaigns` (title, slug, tagline, story markdown, goal_amount, tiers[], status, contingency_note) and `sponsor_pledges` (sponsor_name, email, org, amount, tier_id, message, display_publicly opt-in, status: pending → approved → invoiced → paid). Pledge-only flow — no payment processing until 501(c)(3) is granted.
- **Auto-seeded first campaign**: "Inside Success TV Feature — Birthright Story" with $25k goal, 4 tiers (Bronze $500 / Silver $2.5k / Gold $5k / Presenting $10k), contingency note about ISTV contract redlines, and story markdown explaining the ROI framing.
- **New frontend pages**: `/campaigns` (list) and `/campaigns/:slug` (detail with tier selector + pledge form). Admin CRUD at `/admin/campaigns` with pledge status controls.
- **`SponsorPill` component + `NonDeductibleNotice` block** (`components/campaigns/CampaignParts.jsx`) — reused on campaign cards, detail hero, pledge form, and homepage teaser. Amber-highlighted disclosure is legally required and shown everywhere sponsor money is discussed.
- **Homepage teaser section**: gold-tinted card between Featured Workshops and Impact Statements showing progress bar, sponsor count, and gold CTA button. Auto-hides if no active campaigns.
- **Sponsorship page updated**: added `NonDeductibleNotice` to the existing `/sponsor` tier page + a cross-link to `/campaigns` so users can find both flows.
- Verified E2E: pledge submission → admin approval → progress + public sponsor list updates on the campaign page.

### Iter 58 — Reorder-only vendor flow + pass-through shipping (Feb 2026)
- **No customization / no file upload**: 7C's patches are existing SKUs with files already on record. Removed the file-upload block from `ProductDetail.jsx`; add-to-cart no longer requires an attachment.
- **Message field simplified**: `build_prefilled_url` sends just `"{product name}, quantity: {n}"` per user example. Vendor email subject also updated to "Reorder · …".
- **Shipping surcharge**: new `shipping_cost` field on `Product` model. Included per unit in `_validate_cart_and_total` line total. Displayed on the product detail page under the vendor note. Editable in AdminProducts drawer (`admin-product-form-shipping-cost`). Set to $4.50 across all 6 patches as a starting placeholder — update after negotiating with 7C's.
- **Prefilled URL** still delivers first/last name, email, phone, full shipping address, product choice ("Other"), quantity, message, referral source. Verified E2E: message reads verbatim "Leather-engraved patch · The bond is the cure, quantity: 3".


### Iter 57 — Middleman flow for 7C's Farmstead patches (Feb 2026)
- **New fulfillment mode**: `fulfillable_via = "vendor_custom_form"` (in addition to printful / lulu). Buyer pays birthright via Stripe, vendor is emailed a fully-prefilled Formester URL + file attachments. Wholesale reconciled out-of-band.
- **Products migrated**: 6 patches flipped from `is_off_site` referral → in-cart middleman at $10 retail / $5 wholesale.
- **Prefilled URL builder**: `utils/vendor_dispatch.build_prefilled_url` composes every 7C form field from the buyer's Stripe checkout data. File filenames are listed inside the Message field (URLs can't prefill file inputs).
- **Attachment uploads**: `POST /api/products/{id}/attachment` accepts PDFs / PNGs / JPGs / SVGs up to 15 MB, stores under `backend/static/attachments/`. Guest-friendly (no auth). Only accepts uploads for products with `fulfillable_via = vendor_custom_form`.
- **CartItem model**: added optional `attachment_ids: List[str]`. `CartContext.addItem(product, qty, { attachment_ids })` merges dedupes across cart interactions.
- **Product detail UI**: purchasable vendor products show an "Upload your artwork" block. Add-to-cart is disabled until at least one file is uploaded.
- **Order dispatch**: extended `utils/order_dispatch.dispatch_order` to route `vendor_custom_form` items through `dispatch_vendor_item` — logs a `vendor_orders` row + emails 7C's via Resend with attachments + prefilled URL. Optional `VENDOR_ORDER_BCC` env var CCs the admin.
- **FulfillmentBadge**: new "Handcrafted by {vendor_name}" green pill for `vendor_custom_form` products.


### Iter 56 — Landing-page object-fit bug + gallery cleanup (Feb 2026)
- **Bug**: `Home.jsx:283` (Founder Collection teaser image) was still using `object-contain` → cream bars top/bottom on the landing page. Also `FounderCollectionPage.jsx:79` and `GalleryArtist.jsx:183`. All flipped to `object-cover` and the AI vision `image_caption` is used as alt.
- **Bug**: when a `kind=hero` queue entry was published, the publish flow demoted the OLD hero into `additional_images`. Buyers ended up with stale photos (e.g., the old white convex mug appearing as a thumbnail next to the new teal mug). Fixed in `routers/image_queue.py` — heroes now replace outright; nothing is demoted.
- **Cleanup**: `scripts/cleanup_demoted_heroes.py` walked every product and removed any `additional_images` URL that wasn't a `published` queue entry of kind=additional. 32 products cleaned.
- **Refund request**: routed to support per system prompt — user must email support@emergent.sh.


### Iter 55 — Bulk publish + retry (Feb 2026)
- Topped-up credits → retried the 7 failed hero generations: all 7 succeeded.
- Created `scripts/bulk_publish_ready.py` to flip every `ready` queue entry to `published` in one pass:
  - **31 heroes** replaced (old hero demoted into `additional_images`).
  - **24 additional shots** appended to their products.
- Mug verified: hero now shows the hand-glazed teal ceramic mug matching the description; the inside-flame shot and old hero remain available as thumbnails.


### Iter 54 — Hero replacement queue + fulfillment badge in admin (Feb 2026)
- **Hero mismatch scan**: new `_llm_propose_hero_replacement` in `routers/image_queue.py` compares description + current hero caption + captions/prompts of additional images. Surfaces only true contradictions (wrong color/shape/material/missing branded detail).
- **Queue model extended**: added `kind: "hero" | "additional"` (default "additional"). Publishing kind=hero replaces `image_url`, demotes the old hero to `additional_images`, and clears the cached caption so the auto-captioner re-runs on the new shot.
- **Two scan buttons** on `/admin/image-queue`: "Scan for missing detail shots" (additional kind) and "Scan for hero mismatches" (hero kind).
- **FulfillmentBadge** now also renders inline on every Admin Products row and every Admin Image Queue row so Mike can see at a glance whether a product is wired for fulfillment or display-only.
- **Bulk run**: hero scan flagged 32/66 products. Generation hit Emergent LLM budget cap mid-run — 25 succeeded (status=ready), 7 marked failed (one-click retry from the row after Mike recharges).


### Iter 53 — Fulfillment pills, sample cart gate, AI search captions, AI image queue (Feb 2026)
- **Phase B — fulfillment routing**: `scripts/route_fulfillment.py` mapped 61 unflagged products → 31 Printful / 13 Lulu / 21 sample.
- **Phase A — pills + cart gate**: new `FulfillmentBadge.jsx` (foundation/partner/artist/sample). Wired into `ProductCard`, `ProductDetail`, `FeaturedCard`. Sample products show "Preview only" and the cart entry-points are hidden. Server-side guard added in `routers/checkout.py` (`_validate_cart_and_total`) so direct API calls also reject sample IDs.
- **Phase C — captions in search**: `routers/search.py` now matches `image_caption` for products and partner profiles.
- **Phase D — AI additional-image queue**:
  - `utils/image_generator.py` — reusable Nano Banana generator (also refactored `regenerate-image` onto it).
  - `routers/image_queue.py` — endpoints `POST scan / GET / POST queue / POST {id}/generate / POST {id}/publish / POST {id}/discard`. Uses Claude Sonnet to compare description vs vision caption and propose a focused second-shot prompt.
  - New collection: `pending_additional_images { id, product_id, product_name, prompt, status: queued|generating|ready|published|failed, image_url, error, created_at, generated_at }`.
  - Frontend: `/admin/image-queue` (`AdminImageQueue.jsx`) — review, generate, publish, discard per row. Linked from AdminHub.
- **Bulk run**: 24 additional images generated and now in `ready` status awaiting Mike's review.


### Iter 52 — Full-frame product images + multi-image gallery (Feb 2026)
- **Problem**: Equip grid + product detail were rendering `object-contain` with white letterbox bars on top/bottom/sides; descriptions referenced details (e.g., "flame stamped on the base") that the single hero shot couldn't show.
- **Fix**:
  - `ProductCard` (Equip grid) → `object-cover`, removed `p-2` padding. Cards now full-bleed.
  - `ProductDetail` hero → square aspect, `object-cover`. No bars.
  - `FounderCollectionRail` `FeaturedCard` → `object-cover`.
  - Backend: `additional_images: List[str]` added to `ProductCreate` + `ProductUpdate`.
  - `ProductDetail` shows main image with clickable thumbnail strip when extras exist (testids: `product-hero-image`, `product-gallery-thumbs`, `product-gallery-thumb-{i}`).
  - `AdminProducts` drawer gains an "Additional image URLs" textarea (one URL per line) + preview row (testid: `admin-product-form-additional-images`).
  - `alt` attribute now uses `image_caption` (AI vision) with name fallback for SEO/a11y.
- Verified end-to-end: PUT `additional_images` on `Secure Bonds Mug` → 3 thumbnails rendered → clicking swapped hero. Reset to `[]` after test.



### Iter 51 — Auto-recaption on image swap (Option 2)
- New `schedule_caption_if_image_changed(db, collection, id, old, new)` helper in `utils/image_caption_agent.py`. Fire-and-forget — caller returns instantly; vision call runs in the background; help-context cache invalidates the moment the new caption lands.
- Wired into every admin path that can change an image:
  - `POST /api/products` (create with image)
  - `PUT /api/products/{id}` (image_url edit)
  - `POST /api/products/{id}/regenerate-image` (AI mockup)
  - `PUT /api/foundation/governing-members/{id}` (board photo swap)
  - `PUT /api/partners/my-profiles/{type}` (partner self-edit on avatar)
- Verified end-to-end: swapped a product's image_url → waited 12s → fresh accurate caption present in DB with `image_caption_source_url` matching the new URL. No manual button press needed.

### Iter 50 — AI image-caption agent (assistant sees every image)
- **Problem yesterday's demo exposed**: the help assistant has no eyes — visitor asked "what's in James Reagan's lap?" → assistant deferred to humans because the photo wasn't text.
- **Approach the user steered toward**: don't burden the admin with typing captions. Have the AI describe each image itself, cache the description in the DB, and let the text-only help assistant read those cached descriptions.
- **New `utils/image_caption_agent.py`** uses Claude Sonnet 4.5 (vision via emergentintegrations) to caption any visitor-facing record (governing_members, partner_profiles, products, research_artifacts) that has an `image_url` but no `image_caption`. ~$0.003 per image; one-time pass on ~14 captionable images cost <$0.05.
- Captions stored on the same record as `image_caption` + `image_caption_source_url` (the latter so we know to re-caption when an image is swapped).
- **`POST /api/admin/image-captions/auto-caption?limit=N&force=bool`** triggers a fresh pass. Admin can also manually override a specific caption via `PUT /api/admin/image-captions/{collection}/{id}` if the AI's description is off.
- **`utils/help_context.py`** now injects `[Photo: …]` / `[Image: …]` annotations alongside leadership/partners/products entries. Updated system prompt teaches the assistant it CAN answer "what does X look like" questions when a caption is present, only declining when there's truly no caption available.
- **AdminHub tile** added for "AI image captions" under AI/Email/Ops.
- **Verified end-to-end:** "What does James Reagan have in his lap?" → assistant answers "an orange tabby cat resting on a cream-colored knit blanket"; identical clarity on the Founding Journal, Founder Collection patches, and Flame Meditation Stool product photos. Sample-leadership images (Hannah Lin etc.) caption correctly with the "this is an illustrative bio" caveat.

### Iter 49 — Wholesale pricing for foundation members + Admin Hub
- **Foundation-member pricing model.** Per-product `wholesale_price` field added to the Product model + AdminProducts UI (next to retail price, with retail-cap validation). When a user with `is_foundation = True` checks out, every line item with a non-null wholesale_price is billed at the wholesale value; products without wholesale stay at retail. Patronage / gallery markup is also zeroed out for foundation users.
- **AI billing at 1:1 passthrough.** `compute_cost()` accepts a `multiplier` override; `record_usage()` passes `1.0` when `user.is_foundation`, dropping the 50% Foundation markup. Verified math: retail $0.090 → foundation $0.060 (exact 1.5×).
- **Admin Users page (`/admin/users`)** — searchable list of all users with the **Foundation member** toggle inline; filter pills (All · Foundation · Admin); top-right counter of current foundation members. `PATCH /admin/users/{id}/foundation-status` endpoint added to `routers/foundation.py`.
- **Operations Hub at `/admin`** — single canonical home for every admin tool. 28 tiles grouped into 5 sections (Content & Catalog · Partners & People · Commerce & Payouts · AI/Email/Ops · Governance & System). Replaces the "remember which admin URL does what" problem. The previous AdminDashboard stats page moved to `/admin/stats` (still accessible from the hub).
- **End-to-end pricing verification:** demo user marked foundation + journal wholesale=$12.50 → 2 × journal at checkout returns $25.00 with `wholesale_applied=True` on each line, `foundation_markup_per_unit=$0.00`. Flipped foundation off → same cart returns $76.00 with `wholesale_applied=False`. Pipeline is correct.

### Iter 48 — AI Help Assistant retrained on full platform context
- **Root cause of yesterday's demo embarrassment** (asked "who is the executive director?" → assistant deferred to humans): the assistant only ever saw the static `help_kb.json` and the top-2 KB snippets in its LLM context. It had zero visibility into governing members, partner profiles, equip catalog, workshops, or published research — so any question that depended on live content fell through to a generic "I can flag a human."
- **New `utils/help_context.py`** — compiles a single compact "platform fact pack" from `foundation_content`, `governing_members`, `partner_profiles` (public, includes sample profiles since they render publicly), `products` (active, top-30 by feature/rank), `workshops`, `research_artifacts`, plus a canonical site map. Cached for 5 min in-memory with admin-callable invalidation. ~8KB injected into every LLM-fallback turn so the assistant knows about every human-readable thing on the site.
- **Rewrote LLM system prompt** to lead with confidence: "Almost every question about the foundation, its people, its programs, its products, its research, or its site structure can be answered directly. Only escalate to support@ for account-specific issues (billing disputes, refund requests, stuck payouts, data deletion)." Added explicit rule to use slug paths verbatim (e.g. `/partner/sample-rosa-mendieta`, not `/partner/rosa-mendieta`).
- **KB additions**: `leadership-executive-director` (James Reagan), `leadership-team` (full governing team), `what-is-birthright` (mission), `partner-apply`, `partner-types`. All deflect at the lexical layer for zero LLM cost.
- **Tightened lexical matcher**: added question-prefix stopwords (`tell, me, about, please, show, give, find, etc.`); removed `answer[:300]` from the scoring blob so incidental answer-text tokens stop creating false positives.
- **20-question regression** all routed correctly: identity, catalog, workshops, mission, login, share-account → KB at $0; specific-partner queries, longitudinal research, refund nuance → LLM with rich context giving on-point answers. Out-of-scope queries (sourdough, SSRIs) gracefully decline.

### Iter 47 — Manual payout flow polished + latent partner-ledger bug fixed
- **Disbursement email now fires from BOTH mark-paid endpoints** — `/admin/referrals/{id}/mark-paid` was previously silent (only `/admin/payouts/credits/{id}/mark-paid?source=off_site_credit` notified). Both now send the same `disbursement_notification` Resend email so partners always learn about a payout the moment an admin marks it paid.
- **Fixed latent partner-ledger bug** — `GET /api/me/payouts` was reading from `db.referral_payouts` (a legacy projection collection with 1 stale doc) while the live attribution flow writes to `db.referrals` (richer schema). Partners would have seen zero earned credits even after real referrals landed. Switched the ledger to read from `db.referrals`, mapping `payout_amount → amount_usd` for frontend compatibility.
- **Partner ledger now exposes** `payout_method`, `payout_reference`, `payout_note` per entry — previously the API stripped them.
- **`PartnerPayouts.jsx`** redesigned the paid row to show inline pill badges (`VIA ZELLE`, `ref ZELLE-TXN-7842-91`) plus an italic foundation note — partners can match the reference against their bank statement at a glance.
- **End-to-end verified on preview:** synthetic $15 earned → admin POST mark-paid (method=zelle, ref=ZELLE-TXN-7842-91, note) → totals shift $125→$110 unpaid / $100→$115 paid → live Resend email sent to demo@birthright.org (resend_id `966a6da3-...`) → partner UI renders the new pill design correctly. Decouples the platform from Stripe Connect for the first artist cohort.

### Iter 46 — Stripe LIVE money flow verified end-to-end
- **Live key applied** (`STRIPE_API_KEY=rk_live_51TgpjzQ...NESHDZ`, restricted key). Permissions probed: checkout/customers/refunds/subscriptions/products/prices all green; Stripe Connect scopes intentionally deferred (artist payouts unlock when first artist is ready).
- **Live webhook secret applied** (`STRIPE_WEBHOOK_SECRET=whsec_Lre6z8...t7FE`).
- **Webhook handler rewritten** in `routers/checkout.py` to bypass a latent bug in `emergentintegrations.StripeCheckout.handle_webhook` — when `webhook_secret` is provided, the lib's `stripe.Event` return type has a `__getattr__` that traps `.get`/`.to_dict_recursive` as key lookups, causing `AttributeError`. New handler verifies the signature with `stripe.Webhook.construct_event`, then re-parses the raw body as plain JSON for safe access. Handles `checkout.session.completed`, `async_payment_succeeded/failed`, `payment_intent.succeeded/failed`, `charge.refunded`, gracefully ignores unknown event types.
- Same fix applied to `routers/subscriptions.py`.
- **End-to-end live verification (real $1 charge):**
  - Session `cs_live_a12YQsDTINGsBmZGes1S8g8d0vKdaKiHB8oj2iycupo4SpBRI6NBqdMb7y` created via live API.
  - User paid with Visa ····2187. Stripe charge `ch_3TguOkQzY4Y8maAP0Yo4kZk4` succeeded.
  - Preview DB txn marked `paid`, `_process_paid_transaction` dispatched, donation record `398e8a7e...` persisted to `donations` collection.
  - Webhook signature enforcement verified with synthetic signed events on preview (200 on valid, 400 on tampered/missing).
- **Pending after next deploy:** verify production webhook endpoint responds correctly to a tampered-signature probe (confirms env vars + new code are live on prod).

### Iter 45 — Resend live + Partner offerings on-site rail
- **Resend live email VERIFIED end-to-end.** DKIM TXT was being blocked by a legacy NameBright NS delegation (`_domainkey.birthright.live` and `_dmarc.birthright.live` were pointing away from Cloudflare to namebrightdns). Removed those NS records → DKIM resolved → Resend domain status flipped to verified → live test email sent successfully to `admin@birthright.org` (Resend send id `eed6a6f6-89e0-4589-af99-0e75d907c8f5`).
- **Partner offerings rail (on-site revenue retention)** — new endpoint `GET /api/partners/{slug}/offerings` lists every product whose `vendor_slug` matches the partner, on-site fulfilled products ranked above partner-fulfilled. `PartnerOfferings.jsx` renders an image grid on `/partner/<slug>` showing all the partner's birthright listings as tiles linking to `/equip/<product-slug>`. Per the core principle "first and foremost for us," visitors are kept on birthright (where the foundation captures attribution + partnership share) before any external link is offered.
- **Directory cards** now show a green `★ N on birthright` pill linking into the profile's offerings anchor, with the legacy "Visit external site" link demoted to small secondary text ("or visit external site"). 7C's Farmstead pill shows `★ 6 ON BIRTHRIGHT`.
- **`GET /api/partners` enriched** with `offering_count` per profile via a single aggregation pipeline — no N+1.

### Iter 44 — Resend live email key wired; Stripe activation guide
- **Resend API key applied** (`RESEND_API_KEY=re_9As...`) and `EMAIL_DRY_RUN=false` set in `/app/backend/.env`. Backend restarted.
- API key proven healthy via SDK sanity check (sending from `onboarding@resend.dev` to the account owner address succeeds).
- **Domain `birthright.live` status: `failed`** on Resend — SPF (MX + TXT on `send.birthright.live`) is verified ✅; **DKIM TXT on `resend._domainkey.birthright.live` is missing from DNS**. User needs to add the single DKIM TXT record in Cloudflare; once propagated, live transactional sends will start automatically without further code changes.
- **Stripe activation guide** written to `/app/memory/STRIPE_ACTIVATION_GUIDE.md` — covers live key, checkout webhook, Connect platform, Connect webhook, and a live $1 verification flow. Awaiting three secrets from user: `STRIPE_API_KEY` (live), `STRIPE_WEBHOOK_SECRET`, `STRIPE_CONNECT_WEBHOOK_SECRET`.

### Iter 43 — Data migration framework + admin system console
- **`utils/data_migrations.py`** — append-only registry of idempotent data migrations. Each migration has a stable string ID, runs at most once per environment, and records its application in `db.system_migrations`.
- **Auto-runs on backend startup** via the existing `@app.on_event("startup")` hook. New environments catch up automatically; existing environments only get net-new migrations.
- **Admin console at `/admin/system`** (linked from Admin home):
  - **Support email addresses** panel: site-wide editable `support_email` + `hello_email`, surfaced via `GET /api/system/settings/public` so frontend reads dynamically.
  - **Data migrations** panel: shows applied vs. pending list with timestamps, "Run pending now" button, "Force re-run all" escape hatch.
- **Five migrations seeded** to lock in the founder collection state (vendor profile, patches, bundle, carousel default ranks, research-pollution cleanup, system_settings defaults).
- **HelpPage now reads `support_email` from settings** so changing the address in admin propagates everywhere without a code deploy.

### Iter 42 — Founders Collection cleanup, $10 pricing, 5-patch bundle, Help close UX, brand casing pass
- **Pricing & framework correction**: all 5 patches dropped to $10 (was $38 placeholder). Revenue framework set to **15% affiliate revenue share** from 7C's Farmstead (no Foundation patronage markup on top — that framing was inaccurate for off-site fulfillment). Stamped via existing `?via=birthright_7cs-farmstead` outbound attribution. Storefront copy now says "+ shipping at checkout".
- **Long-form descriptions** verbatim from `/shop/patches` for all 5 patches (no shortened blurbs).
- **Bundle SKU added**: `founder-patch-bundle-all-five` at $40 (saves $10 vs 5×$10), minimal copy with pointer to individual product pages for the full narratives.
- **Founder rail reorder**: patches and bundle now lead the rail; patch-02 ("founder of love story") is the homepage feature (Hat Pair flag cleared).
- **Hat image fit** on ProductDetail: aspect-square → aspect-[4/3], removed inner padding.
- **Help close UX** — 5 close affordances: bigger X (40×40 hit target), backdrop tap-outside, ESC key, swipe-down grab handle, "Close chat" link in footer.
- **Research artifact pollution** removed — 24 regression-test "Admin-Approve-Me" rows wiped from `research_artifacts`.
- **Brand casing pass**: 79 mid-sentence "Birthright" → "birthright" replacements across 37 files (sentence-start instances preserved). Help agent name lowercased to "birthright Help".
- **Help KB expanded**: 9 new entries (patch-bundle, patch-shipping, patch-revenue-share, donate, careers, sponsorship, press-media, data-privacy, gift-purchase, homepage-tour) — now 24 total entries, raising deflection rate.

### Iter 41 — Agentic Concierge removed; Founder Collection patches; lightweight Help assistant
- **Patches in storefront**: 5 leather-engraved patches added to Founder Collection under collection=`founder_collection`, fulfilled off-site by **7C's Farmstead** (custom-order URL). Reused existing `is_off_site` + outbound-click attribution. Editorial intro paragraph added above the rail. "Founder of your love story" patch promoted to `is_homepage_feature`.
- **Research sample fix**: broken Unsplash cover for the Co-Regulation Practices brief replaced with a stable URL.
- **Help assistant** (new): KB-first deflection (free for ~70% of questions) + Claude Haiku 4.5 fallback (~$0.001/turn). Floating "Need help?" pill bottom-left on every page, full-page UI at `/help`, footer link "Help · Ask the AI", session persistence in localStorage, escalate-to-human button.
  - Files: `backend/routers/help_assistant.py`, `backend/data/help_kb.json` (14 entries), `frontend/src/components/HelpAssistant.jsx`, `frontend/src/pages/HelpPage.jsx`
  - 9 pytests passing (`tests/test_iter40_help_assistant.py`)
- **Agentic Concierge removed**: deleted `routers/assistant.py`, `components/AssistantWidget.jsx`, `tests/test_iter26_assistant.py`, and the assistant test class from `test_iter27_ai_billing.py`. Full source archived at `/app/archive/agentic_concierge/` with a learning-oriented README covering the `<<ACTION>>` block protocol, tier-based executor, and restore recipe.

### Iter 39 — Tier-history audit timeline + Shareable tier achievement
- `db.artist_tier_history` ledger logging tier transitions going forward (initial baseline pre-dismissed, real UP/DOWN transitions tracked)
- `utils/artist_tier.log_tier_change()` invoked from `resolve_artist_tier` — fires once per tier_key change
- `GET /api/partner/me/tier-history` — rows + `pending_share` (unacknowledged UP transition)
- `POST /api/partner/me/tier-history/{id}/dismiss-share` — owner-checked acknowledgement
- `GET /api/share/artist/{slug}/tier-card.png` and `.svg` — public Open-Graph-friendly 1200×630 share card, Pillow-rendered (no external service cost), referral_url funneled through `/api/r/{code}` so any visit drives inbound attribution back to the artist
- `ArtistStudio.jsx` — celebration banner with Share / Download PNG / Download SVG / Copy share text buttons + vertical tier-history timeline
- 6 pytest cases passing (`tests/test_iter39_tier_history_share.py`)

### Patch Series marketing assets
- v4 + v4-landscape + v4-multi (IG square / IG Story / Twitter)
- `/marketing` index page + `/fb-promo` gallery (link-only, not in nav)

### Foundation Revenue · POD Margin tile
- `GET /api/admin/foundation/revenue/pod-margin?days=N` (admin-gated)
- Mounted on `/admin` dashboard below StatsGrid
- 4 pytest cases passing

### Artist Partnership — Tracks 1+2+3 + tier system (this session)
- **Patronage payouts** (artist gets list price, Foundation kept 20% buyer markup): `db.artist_sale_payouts` ledger, checkout hook in `_create_order_from_txn`, idempotent
- **Tiered economics**:
  - 🌱 Emerging $0–$5K, 10% in, 0% out
  - 🌿 Sustaining $5K–$15K, 8% in, 2% out
  - 🌳 Established $15K–$40K, 6% in, 4% out
  - 🌸 Thriving $40K–$100K, 5% in, 6% out
  - 🌟 Flourishing $100K+, 5% in, 8% out
- Outbound = marginal brackets (progressive-tax style)
- Basis = trailing-12-month Birthright-attributed revenue (on-site at list + off-site self-reported with `?via=birthright`)
- **Inbound referrals** for artists: extended `resolve_referral_for_checkout` to accept artist partner type, uses tier-based pct, first-purchase-only guard per (artist, buyer) pair
- **Off-site (outbound)** flow: lifted `is_off_site` + `external_url` allowance to artworks via `ArtworkCreate.is_off_site/external_url`; quarterly self-reporting via existing `partner_sales_reports`
- **Admin tools**: `GET /admin/artist/payouts`, `POST /admin/artist/payouts/{id}/mark-paid`, `GET/POST /admin/artist/tier-overrides`
- **Artist dashboard tier card** on `/artist/studio` (current tier + basis + runway to next + override reason if applicable)
- **Public clarity page** `/partner/artist` — exhaustive Artist Partnership Terms with live tier table, worked examples, attribution rules, non-negotiables. Clarity-before-commitment honored.
- **6 pytest cases passing** (boundary tier math, marginal bracket math at all tiers incl. $250K Flourishing example landing at $16,800, public tier-table endpoint shape, patronage payout creation & idempotency)

## P0 / Active
- *None* — Tracks 1+2+3+tier system shipped, tested, and documented to user.

## P3 / Backlog
- Artist `/partner/me/off-site-report` UI page (data layer already exists via `partner_sales_reports`).
- Stripe Connect for auto-payout to artists (currently manual admin-disbursement).
- Public artwork detail UI surfacing of "Ships from artist's studio" badge + dual CTA (patronage / off-site).
- Push & deploy preview → birthright.live.
- Foundation revenue dashboard tile sparkline.
- Additional marketing campaign packs under `/marketing`.

## Key Files (this session)
- `/app/backend/utils/artist_tier.py` (new — tier resolver + marginal-bracket math)
- `/app/backend/routers/artist_partnership.py` (new — payouts + tier + admin)
- `/app/backend/routers/checkout.py` (added patronage payout hook)
- `/app/backend/routers/referrals.py` (artist-aware attribution + first-purchase guard)
- `/app/backend/routers/gallery.py` (added artist_external_url + is_off_site to ArtworkCreate/Update)
- `/app/backend/server.py` (router registration)
- `/app/backend/tests/test_iter38_artist_partnership.py` (new — 6 cases)
- `/app/frontend/src/pages/ArtistPartnershipTerms.jsx` (new — public clarity page)
- `/app/frontend/src/pages/ArtistStudio.jsx` (added ArtistTierCard)
- `/app/frontend/src/App.js` (route `/partner/artist`)

## 3rd-Party Integrations
- Gemini Nano Banana via Emergent LLM key
- Claude Sonnet 4.5 via Emergent LLM key
- Stripe / Printful / Lulu / Resend — user keys

## Test Credentials
See `/app/memory/test_credentials.md`.
