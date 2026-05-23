import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../lib/api";
import { Copy, TrendingUp, ExternalLink } from "lucide-react";

function fmtUSD(n) {
  return `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function PartnerEarningsCard({ profile }) {
  const [link, setLink] = useState(null);
  const [earnings, setEarnings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (profile.partner_type !== "community") {
      setLoading(false);
      return;
    }
    Promise.all([
      api.get(`/referrals/my-link/${profile.partner_type}`),
      api.get("/referrals/my-earnings"),
    ])
      .then(([l, e]) => { setLink(l.data); setEarnings(e.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [profile.partner_type, profile.id]);

  // Only community partners earn via referrals (in v1). Other types: skip the card.
  if (profile.partner_type !== "community") return null;
  if (loading) return <div className="card p-4 text-sm text-[#5C6B6B]">Loading earnings…</div>;
  if (!earnings) return null;

  const fullLink = link ? `${window.location.origin}${link.base_path}` : null;
  const copy = async (value, label) => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(`${label} copied`);
    } catch {
      toast.error("Copy failed — please copy manually");
    }
  };

  return (
    <div className="card p-5 space-y-4" data-testid={`partner-earnings-${profile.id}`}>
      <div>
        <span className="label inline-flex items-center gap-1"><TrendingUp size={11} strokeWidth={1.5} /> Referral earnings</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center" data-testid="earnings-summary">
        <SummaryStat label="Pending" value={fmtUSD(earnings.summary.pending_payout)} color="#C9A961" />
        <SummaryStat label="Lifetime" value={fmtUSD(earnings.summary.lifetime_total)} color="#476B6B" />
        <SummaryStat label="Paid" value={fmtUSD(earnings.summary.paid_to_date)} color="#2E5C46" />
      </div>

      {fullLink && (
        <div className="border-t border-[#E5E1D8] pt-4 space-y-2" data-testid="referral-link-block">
          <p className="label">Your referral link</p>
          <p className="text-xs text-[#5C6B6B]">Anyone who lands on the site via this link is attributed to you for 30 days. Earn {earnings.summary.lifetime_total > 0 ? "the configured" : "your plan's"} revenue share on every workshop they register for and every product they buy.</p>
          <div className="flex gap-2">
            <input readOnly value={fullLink} className="input-field text-xs flex-1" data-testid="referral-link-input" />
            <button onClick={() => copy(fullLink, "Link")} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="copy-referral-link">
              <Copy size={12} strokeWidth={1.5} /> Copy
            </button>
          </div>
          <p className="text-xs text-[#5C6B6B]">
            Or share your shorter <strong>code</strong>:{" "}
            <button onClick={() => copy(link.code, "Code")} className="font-mono text-[#476B6B] hover:underline">{link.code}</button>
          </p>
        </div>
      )}

      {earnings.recent.length > 0 && (
        <div className="border-t border-[#E5E1D8] pt-4">
          <p className="label">Recent attributions</p>
          <ul className="mt-2 divide-y divide-[#E5E1D8] text-sm" data-testid="referral-recent">
            {earnings.recent.slice(0, 5).map((r) => (
              <li key={r.id} className="py-2 flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate">{r.subject_label || `${r.subject_type} #${r.subject_id.slice(0, 8)}`}</p>
                  <p className="text-[10px] text-[#5C6B6B]">
                    {new Date(r.earned_at).toLocaleDateString()} · {r.subject_type} · {r.rev_share_pct}% of {fmtUSD(r.order_total)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{fmtUSD(r.payout_amount)}</p>
                  <p className={`text-[10px] uppercase tracking-wider ${r.status === "paid" ? "text-[#2E5C46]" : "text-[#C9A961]"}`}>{r.status}</p>
                </div>
              </li>
            ))}
          </ul>
          <Link to="/dashboard/reports" className="text-xs text-[#476B6B] hover:underline inline-flex items-center gap-1 mt-3" data-testid="view-full-reports">
            View full reports <ExternalLink size={11} strokeWidth={1.5} />
          </Link>
        </div>
      )}
    </div>
  );
}

function SummaryStat({ label, value, color }) {
  return (
    <div className="border border-[#E5E1D8] rounded p-3">
      <p className="font-serif text-xl" style={{ color }}>{value}</p>
      <p className="text-[10px] uppercase tracking-wider">{label}</p>
    </div>
  );
}
