import React from "react";
import { Link } from "react-router-dom";
import { Sparkles, Telescope, ShoppingBag, MessageSquare, ArrowRight, Wallet, ShieldCheck } from "lucide-react";

export default function AiOverview() {
  return (
    <div className="container-page py-16" data-testid="ai-overview-page">
      <span className="label">Birthright AI</span>
      <h1 className="editorial-h1 mt-2">Working alongside our partners</h1>
      <p className="text-lg text-[#5C6B6B] mt-3 max-w-2xl">
        Three purpose-built AI tools, designed for the way birthright partners actually work — and
        billed honestly: you pay only what the underlying model costs us. No subscription markup. No surprises.
      </p>
      <div className="divider-flame" />

      <div className="grid md:grid-cols-3 gap-5 mt-8">
        <ToolCard
          icon={MessageSquare}
          title="Birthright Concierge"
          eyebrow="For everyone — free"
          body="A site-wide guide that can answer questions, navigate you to pages, fill forms, and take actions on your behalf (with confirmation). Open it via the floating button on any page or press /."
          to="/"
          ctaLabel="Try it on any page"
        />
        <ToolCard
          icon={Telescope}
          title="AI Research Collaborator"
          eyebrow="For research partners"
          body="A peer-level scholarly collaborator: synthesize literature, map a topic's landscape, generate tractable research questions, critique your draft's methodology, plus drafting helpers (summarize notes, suggest tags, polish). Anchored to attachment, family systems, and adjacent literatures — never fabricates citations."
          to="/partner/apply?partner_type=research"
          ctaLabel="Apply as research partner"
        />
        <ToolCard
          icon={ShoppingBag}
          title="Vendor Product AI"
          eyebrow="For vendor partners"
          body="Write product descriptions in our brand voice, suggest a price tier from the catalog, draft marketing blurbs, and generate product images with Nano Banana — all directly inside your product editor."
          to="/partner/apply?partner_type=vendor"
          ctaLabel="Apply as vendor partner"
        />
      </div>

      <h2 className="font-serif text-2xl mt-16">How billing works</h2>
      <div className="divider-flame mt-3 mb-6" />
      <div className="grid md:grid-cols-3 gap-5">
        <Pillar
          icon={Wallet}
          title="1.5× — supports the foundation"
          body="You pay the underlying AI provider cost plus a 50% markup that funds birthright Foundation. Disclosed at every payment point. Top up your AI Wallet in $10/$25/$50/$100 packs via Stripe."
        />
        <Pillar
          icon={ShieldCheck}
          title="No surprise bills"
          body="Every call shows you the cost before it runs and again after. If your wallet runs low, we won't run a call you can't afford — we'll show a top-up card instead."
        />
        <Pillar
          icon={Sparkles}
          title="$1 to start"
          body="When admin approves your partner application, we credit your wallet with $1 so you can try the tools before topping up. Enough for ~25–50 research calls."
        />
      </div>

      <h2 className="font-serif text-2xl mt-16">Roughly how much things cost</h2>
      <div className="divider-flame mt-3 mb-6" />
      <table className="w-full text-sm card" data-testid="cost-table">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
            <th className="text-left px-3 py-2">Tool</th>
            <th className="text-left px-3 py-2">Typical call</th>
            <th className="text-right px-3 py-2">Approx. cost</th>
          </tr>
        </thead>
        <tbody>
          <Row tool="Research · Synthesize literature (brief)" call="~250 words" cost="≈ $0.012" />
          <Row tool="Research · Synthesize literature (deep)" call="~1200 words" cost="≈ $0.045" />
          <Row tool="Research · Map landscape" call="structured JSON" cost="≈ $0.010" />
          <Row tool="Research · Critique methodology" call="full critique" cost="≈ $0.020" />
          <Row tool="Research · Suggest tags" call="quick JSON" cost="≈ $0.001" />
          <Row tool="Vendor · Write description" call="~120 words" cost="≈ $0.005" />
          <Row tool="Vendor · Generate image (Nano Banana)" call="1 image" cost="$0.040" />
          <Row tool="Concierge" call="per turn (partners only)" cost="≈ $0.005" />
        </tbody>
      </table>
      <p className="text-xs text-[#5C6B6B] mt-2">
        Approximate — your actual cost varies with input length. Concierge is free for participants and visitors; only signed-in partners and facilitators are metered.
      </p>

      <div className="card p-8 mt-12 bg-[#FFF8E1] border-[#C9A961]">
        <h3 className="font-serif text-xl">Ready to start?</h3>
        <p className="text-sm text-[#5C6B6B] mt-2">
          Sign in to access your AI Wallet, or apply as a partner to unlock the Research Collaborator and Vendor PDM AI.
        </p>
        <div className="flex flex-wrap gap-3 mt-4">
          <Link to="/login" className="btn-primary text-sm" data-testid="ai-overview-signin">Sign in</Link>
          <Link to="/partner/apply" className="btn-outline text-sm" data-testid="ai-overview-apply">Apply as a partner</Link>
        </div>
      </div>
    </div>
  );
}

function ToolCard({ icon: Icon, title, eyebrow, body, to, ctaLabel }) {
  return (
    <div className="card p-5">
      <Icon size={20} strokeWidth={1.4} className="text-[#476B6B]" />
      <p className="label mt-3 text-[#C9A961]">{eyebrow}</p>
      <h3 className="font-serif text-xl mt-1">{title}</h3>
      <p className="text-sm text-[#5C6B6B] mt-2">{body}</p>
      <Link to={to} className="inline-flex items-center gap-1 mt-4 text-sm text-[#476B6B] hover:underline">
        {ctaLabel} <ArrowRight size={12} />
      </Link>
    </div>
  );
}

function Pillar({ icon: Icon, title, body }) {
  return (
    <div className="card p-5">
      <Icon size={18} strokeWidth={1.4} className="text-[#476B6B]" />
      <h3 className="font-serif text-lg mt-2">{title}</h3>
      <p className="text-sm text-[#5C6B6B] mt-1">{body}</p>
    </div>
  );
}

function Row({ tool, call, cost }) {
  return (
    <tr className="border-t border-[#E5E1D8]">
      <td className="px-3 py-2 text-sm">{tool}</td>
      <td className="px-3 py-2 text-sm text-[#5C6B6B]">{call}</td>
      <td className="px-3 py-2 text-sm text-right font-mono">{cost}</td>
    </tr>
  );
}
