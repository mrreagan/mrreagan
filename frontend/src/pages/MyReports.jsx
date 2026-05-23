import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { BarChart3, Users, Heart, MessageSquare, DollarSign, Star, ExternalLink, TrendingUp } from "lucide-react";

function fmtUSD(n) {
  return `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function MyReports() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/me/reports").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (!user) return null;
  if (loading) return <div className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</div>;
  if (!data) return null;

  const e = data.engagement;
  const f = data.finance;
  const p = data.partner;

  return (
    <div className="container-page py-12" data-testid="my-reports-page">
      <span className="label">Your reports</span>
      <h1 className="editorial-h1 mt-2">Engagement & finance</h1>
      <div className="divider-flame" />

      <section data-testid="engagement-section">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><BarChart3 size={16} strokeWidth={1.5} /> Engagement</h2>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
          <Stat icon={Users} label="Registrations" value={e.registrations} />
          <Stat icon={Heart} label="Workshops attended" value={e.workshops_attended} />
          <Stat icon={Star}  label="Reviews written" value={e.reviews_written} />
          <Stat icon={Heart} label="Impact statements" value={e.impact_statements} />
          <Stat icon={MessageSquare} label="Discussions" value={e.discussions_posted} />
        </div>
      </section>

      <section className="mt-12" data-testid="finance-section">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><DollarSign size={16} strokeWidth={1.5} /> Your spending</h2>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="card p-4 md:col-span-1">
            <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">Lifetime</p>
            <p className="font-serif text-3xl mt-1">{fmtUSD(f.lifetime_spend)}</p>
          </div>
          <Stat label="Workshops" value={fmtUSD(f.by_category.workshops)} small />
          <Stat label="Shop"      value={fmtUSD(f.by_category.shop)} small />
          <Stat label="Sponsorship" value={fmtUSD(f.by_category.sponsorship)} small />
          <Stat label="Donations" value={fmtUSD(f.by_category.donations)} small />
        </div>
      </section>

      {p && (
        <section className="mt-12" data-testid="partner-section">
          <h2 className="font-serif text-xl inline-flex items-center gap-2"><TrendingUp size={16} strokeWidth={1.5} /> Partner earnings</h2>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="card p-4 md:col-span-1 bg-[#FAF8F5]">
              <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">Pending payout</p>
              <p className="font-serif text-3xl mt-1">{fmtUSD(p.referrals.pending_payout)}</p>
            </div>
            <Stat label="Lifetime referral total" value={fmtUSD(p.referrals.lifetime_total)} small />
            <Stat label="Paid to date" value={fmtUSD(p.referrals.paid_to_date)} small />
            <Stat label="Referrals (count)" value={p.referrals.count} small />
            <Stat label="Link clicks" value={p.referrals.clicks} small />
          </div>
          {p.active_subscriptions.length > 0 && (
            <div className="mt-4 card p-4" data-testid="active-subs-summary">
              <p className="label">Active subscriptions</p>
              <ul className="mt-2 text-sm divide-y divide-[#E5E1D8]">
                {p.active_subscriptions.map((s) => (
                  <li key={s.plan_id} className="py-2 flex items-center justify-between">
                    <span className="capitalize">{s.partner_type}</span>
                    <span className="text-xs text-[#5C6B6B]">Expires {new Date(s.expires_at).toLocaleDateString()}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Link to="/dashboard/partner" className="text-xs text-[#476B6B] hover:underline inline-flex items-center gap-1 mt-4" data-testid="back-to-workspace">
            Back to partner workspace <ExternalLink size={11} strokeWidth={1.5} />
          </Link>
        </section>
      )}
    </div>
  );
}

function Stat({ icon: Icon, label, value, small }) {
  return (
    <div className="card p-4">
      {Icon && <Icon size={14} strokeWidth={1.5} className="text-[#C9A961]" />}
      <p className={`${small ? "font-serif text-xl" : "font-serif text-2xl"} mt-1`}>{value}</p>
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</p>
    </div>
  );
}
