import React from "react";
import { Link } from "react-router-dom";
import {
  ShoppingBag, Store, Sparkles, Image as ImageIcon, Microscope, Calendar,
  Users, UserPlus, Briefcase, FileText, Wallet, DollarSign,
  RotateCcw, Mail, Bot, BarChart3, Scale, Shield, ShieldCheck, Server, FlaskConical,
  KeyRound,
  ArrowRight,
} from "lucide-react";

/**
 * Admin Hub — single canonical home for every admin tool in the platform.
 *
 * Each card maps to a specific admin route that's already wired in App.js.
 * Grouped by workflow so an operator can find the right surface without
 * memorizing 20+ URLs.
 */
const SECTIONS = [
  {
    title: "Content & Catalog",
    items: [
      { to: "/admin/products", icon: ShoppingBag, label: "Products (Equip)", desc: "Retail catalog: prices, inventory, images, wholesale prices, founder-collection rank." },
      { to: "/admin/image-queue", icon: ImageIcon, label: "Additional images queue", desc: "AI scans product descriptions for details missing from the hero photo and queues a second shot for review." },
      { to: "/admin/vendor-products", icon: Store, label: "Vendor products", desc: "Partner-fulfilled goods routed through birthright; moderation + attribution." },
      { to: "/admin/featured", icon: Sparkles, label: "Featured items", desc: "Pin partners + products to the homepage and directory front." },
      { to: "/admin/founder-carousel", icon: Sparkles, label: "Founder Collection carousel", desc: "Reorder the 3-slot swipeable teaser at the top of /equip." },
      { to: "/admin/workshops", icon: Calendar, label: "Workshops", desc: "Create, schedule, edit, and publish workshop offerings." },
      { to: "/admin/photos", icon: ImageIcon, label: "Photos", desc: "Hero + workshop imagery library." },
      { to: "/admin/research", icon: Microscope, label: "Research artifacts", desc: "Published briefs, longitudinal case studies, paper metadata." },
    ],
  },
  {
    title: "Partners & People",
    items: [
      { to: "/admin/partners", icon: Users, label: "Partner profiles", desc: "Active partner network — toggle Foundation-member status here for wholesale pricing + 1:1 AI billing." },
      { to: "/admin/partners/prospects", icon: UserPlus, label: "Partner prospects", desc: "Inbound applications: triage, accept, decline." },
      { to: "/admin/gallery/prospects", icon: ImageIcon, label: "Gallery artist prospects", desc: "Artist applications + portfolio review queue." },
      { to: "/admin/foundation/applications", icon: Briefcase, label: "Foundation role applications", desc: "Applications for governing officer / staff openings." },
      { to: "/admin/foundation/roles", icon: FileText, label: "Foundation roles", desc: "Define open seats shown on /lead." },
      { to: "/admin/agreements", icon: FileText, label: "Partner agreements", desc: "Signed terms tracking + W9 status per partner." },
    ],
  },
  {
    title: "Commerce & Payouts",
    items: [
      { to: "/admin/payouts", icon: Wallet, label: "Partner payouts", desc: "Earned-credit ledger across referrals + off-site sales; mark paid manually (Zelle/ACH/check)." },
      { to: "/admin/artist-payouts", icon: DollarSign, label: "Artist payouts", desc: "Gallery artist accrued share + Stripe Connect status (when activated)." },
      { to: "/admin/partner-sales-reports", icon: BarChart3, label: "Partner sales reports", desc: "Monthly earnings, conversion, top performers, exportable CSVs." },
      { to: "/admin/refunds", icon: RotateCcw, label: "Refunds", desc: "Customer refund queue with Stripe cascade + partner debit handling." },
      { to: "/admin/subscriptions", icon: Wallet, label: "Subscriptions", desc: "Sponsorship recurring billing, member tiers, churn." },
      { to: "/admin/campaigns", icon: DollarSign, label: "Sponsor campaigns", desc: "Target-specific sponsorship drives + pledge review. Pledge-only until 501(c)(3) status is granted." },
      { to: "/admin/reports", icon: BarChart3, label: "Financial reports", desc: "Revenue, POD margin, top categories, donor cohorts." },
    ],
  },
  {
    title: "AI, Email & Ops",
    items: [
      { to: "/admin/ai-usage", icon: Bot, label: "AI usage & wallets", desc: "Per-user AI wallet balances, top-ups, debits, and feature breakdown. Foundation users bill at 1:1 passthrough." },
      { to: "/admin/image-captions", icon: ImageIcon, label: "AI image captions", desc: "Auto-generated descriptions of every visitor-facing image, used by the help assistant to answer questions about photos. Run a fresh pass anytime." },
      { to: "/admin/email-ops", icon: Mail, label: "Email operations", desc: "Outbound log (Resend), bounce reports, send-status diagnostics." },
      { to: "/admin/studio", icon: Sparkles, label: "Studio (image gen)", desc: "Bulk image generation jobs for products and content." },
      { to: "/admin/studio/queue", icon: Sparkles, label: "Studio queue", desc: "Pending and completed image-gen tasks." },
      { to: "/admin/lulu-ops", icon: FileText, label: "Lulu print-on-demand", desc: "Book/print order routing, status callbacks, error queue." },
    ],
  },
  {
    title: "Governance & System",
    items: [
      { to: "/admin/governance", icon: Scale, label: "Governance proposals", desc: "Manage proposals, votes, and member roster shown on /lead." },
      { to: "/counsel", icon: FileText, label: "Legal document downloads", desc: "Every draft artefact + working-draft workflow (upload, diff, release, history)." },
      { to: "/admin/system", icon: Server, label: "System status", desc: "Data migrations, deployment state, sanity diagnostics." },
      { to: "/admin/users", icon: Shield, label: "Users & members", desc: "All registered users. Toggle the Foundation-member flag here for wholesale equip pricing + 1:1 AI billing." },
      { to: "/admin/stats", icon: BarChart3, label: "Stats dashboard", desc: "Headline KPI counters and POD-margin tiles (the page formerly at /admin)." },
      { to: "/admin/counsel-review", icon: FileText, label: "Counsel review checklist", desc: "Two-checkbox (manual + auto) tracking of counsel's review of every legal draft. Visible to counsel and admin." },
      { to: "/admin/legal/ratifications", icon: Scale, label: "Legal ratifications", desc: "Mark drafts counsel-ratified, track redlines, apply roundtrips." },
      { to: "/admin/settings/counsel", icon: KeyRound, label: "Counsel credentials", desc: "Rotate the counsel email + password. Persists across redeploys." },
      { to: "/admin/counsel-activity", icon: ShieldCheck, label: "Counsel activity log", desc: "Full URL-by-URL audit trail of counsel sessions. Admin-only — counsel cannot view their own log." },
      { to: "/admin/user-activity", icon: Shield, label: "User activity & admin trace", desc: "Tier 1 security events (all users) + Tier 2 URL trace of every admin session. 365-day retention. Admin-only." },
    ],
  },
];

export default function AdminHub() {
  return (
    <div className="container-page max-w-6xl py-10" data-testid="admin-hub">
      <header className="mb-10">
        <span className="label text-[#C9A961]">Admin</span>
        <h1 className="font-serif text-4xl mt-1">Operations hub</h1>
        <p className="text-sm text-[#5C6B6B] mt-2 max-w-prose">
          Every administrative surface in one place. Click into any tool to manage that part of the foundation.
        </p>
      </header>

      <div className="space-y-12">
        {SECTIONS.map((sec) => (
          <section key={sec.title} data-testid={`admin-section-${sec.title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
            <h2 className="font-serif text-xl mb-4 pb-2 border-b border-[#E5E1D8]">{sec.title}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sec.items.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className="card p-5 hover:border-[#476B6B] transition group flex flex-col"
                    data-testid={`admin-tile-${item.to.replace(/[^a-z0-9]/gi, "-")}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <Icon size={20} strokeWidth={1.5} className="text-[#C9A961] shrink-0 mt-0.5" />
                      <ArrowRight size={14} strokeWidth={1.5} className="text-[#5C6B6B] group-hover:text-[#476B6B] transition" />
                    </div>
                    <p className="font-serif text-base mt-3">{item.label}</p>
                    <p className="text-xs text-[#5C6B6B] mt-1.5 leading-relaxed">{item.desc}</p>
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
