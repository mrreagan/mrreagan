/**
 * AdminRoadmap — Production readiness + backlog status board.
 *
 * Categorised checklist covering:
 *   - Production dependencies that are built but blocked on external systems
 *   - Features built in backend but not yet surfaced in UI
 *   - Mocked/placeholder content that must be replaced before launch
 *   - Features conceptually planned but not built yet
 *   - Admin-only pages (starred so they're not user-facing)
 *
 * Convention:
 *   * (star) = admin-only page OR built-but-not-implemented OR not-built-yet
 *   Status pills:
 *     built            — code exists, works, in prod
 *     built_not_wired  — built in backend, no user-facing UI yet
 *     mocked           — placeholder data or fake flow, must replace pre-launch
 *     blocked          — dependent on external decision (identity mgmt, tax status, etc.)
 *     not_built        — planned but no code yet
 */
import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  AlertTriangle,
  Circle,
  Lock,
  Wrench,
  Eye,
  Star,
} from "lucide-react";

const STATUS_META = {
  built: { label: "Built & live", color: "bg-[#E5F0E8] text-[#01784E]", icon: Check },
  built_not_wired: { label: "Built · not yet in UI", color: "bg-[#FBF3E4] text-[#8B4513]", icon: Wrench },
  mocked: { label: "Mocked / placeholder", color: "bg-[#F9E5E1] text-[#8B0000]", icon: Circle },
  blocked: { label: "Blocked (external)", color: "bg-[#EDEDED] text-[#3A3A3A]", icon: Lock },
  not_built: { label: "Not built yet", color: "bg-[#EDEDED] text-[#5C6B6B]", icon: Circle },
};

const SECTIONS = [
  {
    id: "blocked",
    title: "1. Blocked on external decisions",
    intro: "These are built or partially built, but cannot go live until an external dependency is resolved. Nothing here is a code problem — they're waiting on legal, tax, or product decisions.",
    items: [
      {
        name: "Identity management / real user auth *",
        location: "Site-wide login/register + partner apply flows",
        status: "mocked",
        note: "Currently mocked. Founder deferred identity provider selection at project outset. All identity-dependent flows (partner apply approvals, sponsor-to-user linking, vendor login, board-member auth) are gated on this decision. Present flow uses local JWT + email/password.",
        blockers: ["Founder decision: stay with JWT+email, or move to Google/Emergent-managed SSO?"],
      },
      {
        name: "Stripe Connect artist payouts (Part D) *",
        location: "/admin/artist-payouts + artist onboarding",
        status: "built_not_wired",
        note: "Backend endpoints and payout tracking are built. Live Stripe Connect account activation deferred until first artist is ready to onboard — avoids KYC data collection with no immediate use.",
        blockers: ["First artist commits to onboard", "Stripe Connect Standard account activation"],
      },
      {
        name: "501(c)(3) tax status recognition *",
        location: "Sponsorship page, Campaigns, receipts",
        status: "blocked",
        note: "Every sponsor-facing surface currently displays 'Not currently tax-deductible' because IRS 501(c)(3) determination has not been submitted. Legal counsel and entity formation must complete first.",
        blockers: ["Birthright Foundation LLC/nonprofit entity formation", "Form 1023-EZ or 1023 filed and approved"],
      },
      {
        name: "Deloitte Outside Employment Approval *",
        location: "Founder onboarding — internal",
        status: "blocked",
        note: "Public revenue-generating activity (workshops, product sales, sponsor invoicing) is gated on founder's OEA approval from Deloitte HR. Preview environment is fully functional so the platform is ready the moment approval lands.",
        blockers: ["OEA form submission", "Deloitte HR written approval"],
      },
      {
        name: "State charitable solicitation registration *",
        location: "Sponsorship, Campaigns",
        status: "blocked",
        note: "CA, NY, FL and others require charity registration before soliciting. Sponsor Partner flow works but should not actively market until entity + registrations exist.",
        blockers: ["Entity formation", "State-by-state Charitable Solicitation registrations (plan doc: 21-charitable-solicitation-plan.docx)"],
      },
    ],
  },
  {
    id: "built_not_wired",
    title: "2. Built in backend, not yet surfaced in UI",
    intro: "Backend/data model is done. Front-end route or admin surface is missing. Small lift to finish — the hard work is behind us.",
    items: [
      {
        name: "Public-facing legal renderer *",
        location: "/legal/:slug (planned) — 21 legal drafts already downloadable at /api/legal/drafts/:slug",
        status: "built_not_wired",
        note: "21 EU-compliant legal drafts + ISTV memo generated and downloadable as .docx from backend. Versioned publish flow to render them as clean HTML pages at /legal/:slug is designed but not built.",
      },
      {
        name: "Sponsor Partner directory listings",
        location: "/partner?partner_type=sponsor",
        status: "built",
        note: "Sponsor Partner records auto-elevate on paid pledges, and partner_profiles rows are created. Filter tab exists on /partner. Will populate as real sponsors come through.",
      },
      {
        name: "Cookie / consent management banner *",
        location: "Site-wide — first page load",
        status: "not_built",
        note: "Legal audit flagged as P1. Should be built alongside ToS + Privacy checkboxes on /register and checkout.",
      },
      {
        name: "Mandatory ToS + Privacy checkboxes at signup/checkout *",
        location: "/register, checkout flow",
        status: "not_built",
        note: "Related to Cookie banner. Legal draft docs 01-terms-of-service and 02-privacy-policy exist as .docx; need to publish HTML versions first (see item 2.1).",
      },
      {
        name: "AI image caption alt attributes *",
        location: "Shop, ProductDetail, FounderCollection, PartnerProfile, Lead",
        status: "not_built",
        note: "Original problem statement asked for image_caption to be wired into <img alt={...}> across product/partner pages for SEO + accessibility. Search index already reads captions; front-end alt tags still pending.",
      },
    ],
  },
  {
    id: "mocked",
    title: "3. Mocked / placeholder content — replace pre-launch",
    intro: "Sample data intentionally seeded to demonstrate how the platform will look with real data. All are flagged with is_sample=true in the DB and hidden from public directories.",
    items: [
      {
        name: "Board members",
        location: "/board (member list) + governance flows",
        status: "mocked",
        note: "All board members currently show is_sample=true. Real board recruits and onboards after entity formation. Governance proposal flow works; votes are recorded but only sample members exist.",
      },
      {
        name: "Sample partner profiles (all types)",
        location: "/partner — hidden by default; visible with ?samples=1",
        status: "mocked",
        note: "Illustrative profiles across all 7 partner types to show what a great Birthright profile looks like. Real partners displace them as they onboard.",
      },
      {
        name: "Legal drafts marked as AI-generated first drafts",
        location: "/admin/legal-docs + counsel download links",
        status: "mocked",
        note: "All 21 drafts explicitly labelled 'not legal advice — AI-generated first draft.' Counsel-returned versions replace these on redeploy.",
      },
      {
        name: "ISTV campaign goal amount ($25k)",
        location: "/campaigns/inside-success-tv-feature",
        status: "mocked",
        note: "Placeholder goal. Edit via /admin/campaigns when actual production budget is finalized.",
      },
    ],
  },
  {
    id: "not_built",
    title: "4. Named in strategy — not built yet",
    intro: "Features you've named or requested that don't have code yet. Prioritized by mission impact.",
    items: [
      {
        name: "Gratitude Desk * (admin-only) *",
        location: "/admin/gratitude (planned)",
        status: "not_built",
        note: "Concept: single-pane view where admin can see all pending thank-yous — sponsor pledges paid, first-time supporters, workshop no-shows to check on, partner milestones. Sends warm outbound touch. NOT public — admin viewable only.",
      },
      {
        name: "Development Desk * (admin-only) *",
        location: "/admin/development (planned)",
        status: "not_built",
        note: "Concept: fundraising/major-gift pipeline. Prospect list, cultivation stage tracking, ask amounts, next-touch dates, sponsor upgrade paths (Contributor → Sponsor Partner → Presenting). NOT public — admin viewable only.",
      },
      {
        name: "First-dollar wall / social-proof marquee *",
        location: "Homepage",
        status: "not_built",
        note: "Rolling ticker showing recent purchases/pledges/registrations (anonymized) — social proof on the landing page. Builds momentum feel once real activity exists.",
      },
      {
        name: "'From the partners' homepage carousel *",
        location: "Homepage",
        status: "not_built",
        note: "Rotating quote/photo card from real partners once directory has enough real (non-sample) profiles.",
      },
      {
        name: "Sponsor thank-you email on level transition *",
        location: "Auto-triggered when Contributor → Sponsor Partner / → Presenting",
        status: "not_built",
        note: "Suggested last iteration. Would announce 'welcome to Sponsor Partner' with a link to complete the partner profile. Big driver of second-time sponsorship.",
      },
      {
        name: "Dynamic Stripe Payment Link per pledge *",
        location: "Campaign pledge invoice email",
        status: "not_built",
        note: "Currently invoice email uses a static Stripe link from env var. Dynamic per-pledge link would auto-mark pledges 'paid' via webhook — zero manual reconciliation.",
      },
      {
        name: "Cookie / consent banner *",
        location: "Site-wide (see also item 2.4)",
        status: "not_built",
      },
    ],
  },
  {
    id: "admin_only_index",
    title: "5. Admin-only pages (starred = admin viewable only)",
    intro: "Reference: every page under /admin is admin-only and requires the admin role. Listed here so you can visually distinguish user-facing vs internal surfaces. All admin pages are protected by role-based auth on top of the identity system (item 1.1).",
    items: [
      { name: "*Admin Hub", location: "/admin", status: "built", note: "Landing page for all admin surfaces." },
      { name: "*Users", location: "/admin/users", status: "built" },
      { name: "*Products (CRUD)", location: "/admin/products", status: "built" },
      { name: "*Image Queue (AI vision)", location: "/admin/image-queue", status: "built" },
      { name: "*Legal Docs", location: "/admin/legal-docs", status: "built" },
      { name: "*Sponsor Campaigns", location: "/admin/campaigns", status: "built", note: "Includes pledges, sponsor partners table, 18-mo degrade sweep." },
      { name: "*Studio (AI product design)", location: "/admin/studio + /admin/studio/queue", status: "built" },
      { name: "*Lulu Ops (book fulfillment)", location: "/admin/lulu-ops", status: "built" },
      { name: "*Email Ops", location: "/admin/email-ops", status: "built" },
      { name: "*Workshops", location: "/admin/workshops", status: "built" },
      { name: "*Photos (workshop galleries)", location: "/admin/photos", status: "built" },
      { name: "*Governance", location: "/admin/governance", status: "built", note: "Board proposals, votes, close/tally. Real board pending item 3.1." },
      { name: "*Partners", location: "/admin/partners", status: "built" },
      { name: "*Payouts (partner revenue share)", location: "/admin/payouts", status: "built" },
      { name: "*Artist Payouts", location: "/admin/artist-payouts", status: "built_not_wired", note: "Blocked on Stripe Connect (item 1.2)." },
      { name: "*Subscriptions", location: "/admin/subscriptions", status: "built" },
      { name: "*Reports", location: "/admin/reports", status: "built" },
      { name: "*Vendor Products", location: "/admin/vendor-products", status: "built" },
      { name: "*Partner Sales Reports", location: "/admin/partner-sales-reports", status: "built" },
      { name: "*Featured items curation", location: "/admin/featured", status: "built" },
      { name: "*Gallery Prospects", location: "/admin/gallery/prospects", status: "built" },
      { name: "*Partner Prospects", location: "/admin/partners/prospects", status: "built" },
      { name: "*Foundation Roles", location: "/admin/foundation-roles", status: "built" },
      { name: "*Foundation Applications", location: "/admin/foundation-applications", status: "built" },
      { name: "*Ombudsman Queue", location: "/admin/ombudsman", status: "built" },
      { name: "*Disputes", location: "/admin/disputes/:id", status: "built" },
      { name: "*Refunds", location: "/admin/refunds", status: "built" },
      { name: "*Founder Carousel curation", location: "/admin/founder-carousel", status: "built" },
      { name: "*System dashboard", location: "/admin/system", status: "built" },
      { name: "*AI Usage & costs", location: "/admin/ai-usage", status: "built" },
      { name: "*Agreements (Partnership + Indemnification versions)", location: "/admin/agreements", status: "built" },
      { name: "*Research moderation", location: "/admin/research", status: "built" },
      { name: "*Roadmap / production readiness (this page)", location: "/admin/roadmap", status: "built" },
    ],
  },
];

function StatusPill({ status }) {
  const meta = STATUS_META[status] || STATUS_META.not_built;
  const Icon = meta.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full ${meta.color}`}
      data-testid={`status-pill-${status}`}
    >
      <Icon size={10} strokeWidth={2} />
      {meta.label}
    </span>
  );
}

function ItemRow({ item }) {
  return (
    <div
      className="border-b border-[#E8E4DC] py-4"
      data-testid={`roadmap-item-${item.name.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`}
    >
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-[240px]">
          <p className="font-serif text-base text-[#0F2424]">{item.name}</p>
          <p className="text-xs text-[#5C6B6B] mt-0.5 font-mono">{item.location}</p>
        </div>
        <StatusPill status={item.status} />
      </div>
      {item.note && (
        <p className="text-sm text-[#3D4A4A] mt-2 leading-relaxed">{item.note}</p>
      )}
      {item.blockers && item.blockers.length > 0 && (
        <div className="mt-2 flex items-start gap-2 text-xs text-[#8B4513] bg-[#FBF3E4] border border-[#E5D7B3] rounded-md px-3 py-2">
          <AlertTriangle size={12} strokeWidth={1.5} className="mt-0.5 shrink-0" />
          <div>
            <strong>Blockers:</strong>
            <ul className="mt-0.5 space-y-0.5">
              {item.blockers.map((b, i) => <li key={i}>· {b}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AdminRoadmap() {
  const [filter, setFilter] = useState("all");

  const counts = useMemo(() => {
    const all = SECTIONS.flatMap((s) => s.items);
    const total = all.length;
    const byStatus = {};
    for (const s of Object.keys(STATUS_META)) byStatus[s] = 0;
    for (const i of all) byStatus[i.status] = (byStatus[i.status] || 0) + 1;
    return { total, byStatus };
  }, []);

  const visibleSections = useMemo(() => {
    if (filter === "all") return SECTIONS;
    return SECTIONS.map((s) => ({
      ...s,
      items: s.items.filter((i) => i.status === filter),
    })).filter((s) => s.items.length > 0);
  }, [filter]);

  return (
    <div className="container-page py-12" data-testid="admin-roadmap-page">
      <Link
        to="/admin"
        className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-4"
      >
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="label">Admin · Internal</span>
          <h1 className="editorial-h1 mt-1">Roadmap &amp; Production Readiness</h1>
        </div>
        <span className="text-xs uppercase tracking-widest text-[#8B4513] bg-[#E5D7B3] px-2 py-0.5 rounded-full font-semibold">
          <Eye size={10} className="inline mr-1" /> Admin-viewable only
        </span>
      </div>

      <div className="divider-flame" />

      <p className="text-sm text-[#5C6B6B] max-w-2xl leading-relaxed mt-4">
        Everything below is either <strong>built and live</strong>, <strong>built but not yet wired to a UI</strong>, <strong>mocked with placeholder data</strong>, <strong>blocked on an external decision</strong>, or <strong>not built yet</strong>. Every entry marked with an asterisk (<strong>*</strong>) is either an admin-only page (not user-facing) OR a page/feature that is not yet built. Blocked and mocked items MUST be resolved before Birthright can be marketed publicly.
      </p>

      {/* Legend */}
      <div className="mt-6 card p-4 bg-[#FAF8F5]">
        <p className="label !mt-0 mb-2">Legend</p>
        <div className="flex flex-wrap gap-3 text-xs">
          <div className="inline-flex items-center gap-2">
            <Star size={12} className="text-[#C9A961]" />
            <span className="text-[#5C6B6B]">
              <strong>*</strong> = admin-only page <em>or</em> not-yet-built / not-yet-implemented
            </span>
          </div>
          {Object.entries(STATUS_META).map(([k, m]) => {
            const Icon = m.icon;
            return (
              <button
                key={k}
                onClick={() => setFilter(filter === k ? "all" : k)}
                className={`inline-flex items-center gap-1.5 px-2 py-1 rounded ${m.color} ${filter === k ? "ring-2 ring-[#0F2424]" : ""}`}
                data-testid={`filter-${k}`}
              >
                <Icon size={11} strokeWidth={2} />
                <span className="text-[10px] uppercase tracking-wider font-semibold">
                  {m.label} · {counts.byStatus[k] || 0}
                </span>
              </button>
            );
          })}
          {filter !== "all" && (
            <button
              onClick={() => setFilter("all")}
              className="text-[10px] underline text-[#476B6B]"
              data-testid="filter-clear"
            >
              Clear filter
            </button>
          )}
        </div>
      </div>

      {/* Sections */}
      <div className="mt-8 space-y-10">
        {visibleSections.map((section) => (
          <section key={section.id} data-testid={`section-${section.id}`}>
            <h2 className="font-serif text-2xl text-[#0F2424]">{section.title}</h2>
            <p className="text-sm text-[#5C6B6B] mt-1 max-w-3xl leading-relaxed">{section.intro}</p>
            <div className="mt-4 card p-6">
              {section.items.map((item, i) => <ItemRow key={i} item={item} />)}
            </div>
          </section>
        ))}
      </div>

      {/* Footnotes */}
      <section className="mt-16 card p-6 bg-[#FAF8F5]" data-testid="roadmap-footnotes">
        <p className="label !mt-0">Footnotes on the asterisks (*)</p>
        <ol className="mt-3 text-sm text-[#3D4A4A] space-y-2 list-decimal ml-5 leading-relaxed">
          <li>
            <strong>Admin-only pages</strong> (all pages under <code className="font-mono text-xs">/admin/*</code>) are visible only to authenticated users with the <code className="font-mono text-xs">admin</code> role. They will remain hidden from public navigation and are additionally gated by the identity management decision (Section 1, item 1).
          </li>
          <li>
            <strong>Built-but-not-implemented pages</strong> — code paths, models, and backend endpoints exist, but the visible UI at the described public URL has not been shipped yet. Small lift to finish; not blocked externally.
          </li>
          <li>
            <strong>Not-built-yet pages</strong> — named in strategy or previously discussed but no code exists. Prioritize based on mission impact (Gratitude Desk and Development Desk are highest-value for the operations team; social-proof marquee is highest-value for public conversion once real activity exists).
          </li>
          <li>
            <strong>Blocked items</strong> are dependent on decisions outside the codebase (entity formation, Deloitte OEA, 501(c)(3), identity provider choice). Code is ready to activate the moment each dependency is resolved.
          </li>
          <li>
            <strong>Mocked items</strong> use <code className="font-mono text-xs">is_sample=true</code> in the database and are automatically hidden from public directories. They will be superseded as real records are created.
          </li>
        </ol>
      </section>
    </div>
  );
}
