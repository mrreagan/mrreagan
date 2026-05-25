import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Scale, Clock, CheckCircle2, XCircle, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";

const STATUS_PILL = {
  open:          { label: "Open",         cls: "bg-[#FFF8E1] text-[#8B7128]",  icon: Clock },
  under_review:  { label: "Under review", cls: "bg-[#E8F0FE] text-[#3458B5]",  icon: Clock },
  resolved:      { label: "Resolved",     cls: "bg-[#E8F0EA] text-[#2E5C46]",  icon: CheckCircle2 },
  dismissed:     { label: "Dismissed",    cls: "bg-[#F2EEE7] text-[#5C6B6B]",  icon: XCircle },
};

export default function MyDisputes() {
  const [rows, setRows] = useState([]);
  const [role, setRole] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get(`/me/disputes?role=${role}`)
      .then((r) => setRows(r.data))
      .catch(() => toast.error("Could not load disputes"))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [role]);

  return (
    <div className="container-page py-12" data-testid="my-disputes-page">
      <span className="label">Dashboard · Disputes</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Scale size={28} strokeWidth={1.2} /> My Disputes
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Disputes you've filed or that are filed about you. An ombudsman reviews each one confidentially.
      </p>

      <div className="flex flex-wrap gap-2 mt-6" data-testid="dispute-filters">
        {[
          { v: "all",     label: "All" },
          { v: "filed",   label: "Filed by me" },
          { v: "against", label: "About me" },
        ].map((c) => (
          <button
            key={c.v}
            onClick={() => setRole(c.v)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              role === c.v ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`dispute-filter-${c.v}`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-8">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="mt-12 text-center py-12 border border-dashed border-[#E5E1D8] rounded">
          <Scale size={40} strokeWidth={1} className="mx-auto text-[#C9A961]" />
          <p className="mt-4 text-sm text-[#5C6B6B]">No disputes here.</p>
        </div>
      ) : (
        <ul className="mt-6 card divide-y divide-[#E5E1D8]" data-testid="my-disputes-list">
          {rows.map((d) => {
            const pill = STATUS_PILL[d.status] || STATUS_PILL.open;
            return (
              <li key={d.id} className="py-4 px-4 flex items-center gap-3" data-testid={`dispute-row-${d.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium truncate">{d.title}</p>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${pill.cls}`}>
                      {pill.label}
                    </span>
                    <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">{d.category}</span>
                  </div>
                  <p className="text-xs text-[#5C6B6B] mt-1 truncate">
                    Filed by <strong>{d.filed_by_user?.name || "—"}</strong>, about <strong>{d.against_user?.name || "—"}</strong>
                  </p>
                  <p className="text-[10px] text-[#5C6B6B]">{new Date(d.created_at).toLocaleString()}</p>
                </div>
                <Link to={`/dashboard/disputes/${d.id}`} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`dispute-open-${d.id}`}>
                  Open <ExternalLink size={12} strokeWidth={1.5} />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
