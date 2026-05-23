import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { BarChart3, DollarSign, TrendingUp, Briefcase, Calendar, ShoppingBag } from "lucide-react";

function fmtUSD(n) {
  return `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function AdminReports() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/admin/reports").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</div>;
  if (!data) return null;

  const { engagement, revenue, payouts, top_partners, top_workshops } = data;

  return (
    <div className="container-page py-12" data-testid="admin-reports-page">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Foundation reports</h1>
      <div className="divider-flame" />

      <section data-testid="admin-engagement">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><BarChart3 size={16} strokeWidth={1.5} /> Engagement</h2>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
          <Stat label="Users" value={engagement.users} />
          <Stat label="Workshops" value={engagement.workshops} />
          <Stat label="Products" value={engagement.products} />
          <Stat label="Reviews" value={engagement.reviews} />
          <Stat label="Active partners" value={engagement.partners_active} />
          <Stat label="Active subs" value={engagement.active_subscriptions} />
          <Stat label="Discussions" value={engagement.discussions} />
          <Stat label="New regs (30d)" value={engagement.new_registrations_30d} />
          <Stat label="New signups (30d)" value={engagement.new_signups_30d} />
        </div>
      </section>

      <section className="mt-12" data-testid="admin-revenue">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><DollarSign size={16} strokeWidth={1.5} /> Revenue</h2>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-3">
          <BigStat label="Workshops"     icon={Calendar}    revenue={revenue.workshops.revenue}     count={revenue.workshops.count} />
          <BigStat label="Shop"          icon={ShoppingBag} revenue={revenue.shop.revenue}           count={revenue.shop.count} />
          <BigStat label="Subscriptions" icon={Briefcase}   revenue={revenue.subscriptions.revenue}  count={revenue.subscriptions.count} />
          <BigStat label="Sponsorship"   icon={TrendingUp}  revenue={revenue.sponsorship.revenue}    count={revenue.sponsorship.count} />
          <BigStat label="Donations"     icon={TrendingUp}  revenue={revenue.donations.revenue}      count={revenue.donations.count} />
          <div className="card p-5 bg-[#FAF8F5] border-[#476B6B]">
            <p className="text-[10px] uppercase tracking-wider text-[#476B6B]">Gross total</p>
            <p className="font-serif text-3xl mt-1">{fmtUSD(revenue.gross_total)}</p>
            <p className="text-xs text-[#5C6B6B] mt-1">All revenue streams combined.</p>
          </div>
        </div>
      </section>

      <section className="mt-12" data-testid="admin-payouts-summary">
        <h2 className="font-serif text-xl">Partner payout liability</h2>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="card p-5">
            <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">Pending payouts owed</p>
            <p className="font-serif text-3xl mt-1">{fmtUSD(payouts.pending_payouts.sum)}</p>
            <p className="text-xs text-[#5C6B6B] mt-1">{payouts.pending_payouts.n} earned referral{payouts.pending_payouts.n === 1 ? "" : "s"} awaiting payout.</p>
          </div>
          <div className="card p-5">
            <p className="text-[10px] uppercase tracking-wider text-[#2E5C46]">Paid to date</p>
            <p className="font-serif text-3xl mt-1">{fmtUSD(payouts.paid_to_date.sum)}</p>
            <p className="text-xs text-[#5C6B6B] mt-1">{payouts.paid_to_date.n} settled payout{payouts.paid_to_date.n === 1 ? "" : "s"}.</p>
          </div>
        </div>
      </section>

      <section className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div data-testid="admin-top-partners">
          <h2 className="font-serif text-xl">Top partners by referral $</h2>
          {top_partners.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] mt-3">No partner referrals yet.</p>
          ) : (
            <ul className="mt-3 card divide-y divide-[#E5E1D8]">
              {top_partners.map((p, i) => (
                <li key={p.partner_user_id} className="py-3 px-4 flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm">
                    <span className="text-[10px] text-[#C9A961] w-4">#{i + 1}</span> {p.name}
                  </span>
                  <span className="text-sm">{fmtUSD(p.total)} <span className="text-[10px] text-[#5C6B6B] ml-1">· {p.count} ref{p.count === 1 ? "" : "s"}</span></span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div data-testid="admin-top-workshops">
          <h2 className="font-serif text-xl">Top workshops by revenue</h2>
          {top_workshops.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] mt-3">No workshop revenue yet.</p>
          ) : (
            <ul className="mt-3 card divide-y divide-[#E5E1D8]">
              {top_workshops.map((w, i) => (
                <li key={w.workshop_id} className="py-3 px-4 flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm truncate">
                    <span className="text-[10px] text-[#C9A961] w-4">#{i + 1}</span> {w.title}
                  </span>
                  <span className="text-sm shrink-0">{fmtUSD(w.revenue)} <span className="text-[10px] text-[#5C6B6B] ml-1">· {w.registrations} reg{w.registrations === 1 ? "" : "s"}</span></span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card p-4">
      <p className="font-serif text-2xl">{value}</p>
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</p>
    </div>
  );
}

function BigStat({ label, icon: Icon, revenue, count }) {
  return (
    <div className="card p-5" data-testid={`revenue-${label.toLowerCase()}`}>
      <Icon size={14} strokeWidth={1.5} className="text-[#C9A961]" />
      <p className="font-serif text-2xl mt-2">{fmtUSD(revenue)}</p>
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label} · {count} transaction{count === 1 ? "" : "s"}</p>
    </div>
  );
}
