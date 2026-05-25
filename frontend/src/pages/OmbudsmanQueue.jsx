import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Scale, AlertTriangle, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";

const STATUS_PILL = {
  open:          "bg-[#FFF8E1] text-[#8B7128]",
  under_review:  "bg-[#E8F0FE] text-[#3458B5]",
};

export default function OmbudsmanQueue() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/admin/ombudsman/queue")
      .then((r) => setData(r.data))
      .catch(() => toast.error("Could not load queue"))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</p>;

  return (
    <div className="container-page py-12" data-testid="ombudsman-queue">
      <span className="label">Admin · Ombudsman</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Shield size={28} strokeWidth={1.2} /> Ombudsman queue
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Disputes awaiting review and DM threads that participants flagged. Reviewing message bodies
        is logged in the audit trail.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-6">
        <Stat label="Open disputes" value={data.counts.open_disputes} testid="stat-open-disputes" />
        <Stat label="Under review" value={data.counts.under_review_disputes} testid="stat-under-review" />
        <Stat label="Flagged DM threads" value={data.counts.flagged_threads} testid="stat-flagged-threads" />
      </div>

      <section className="mt-10" data-testid="dispute-queue-section">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><Scale size={16} strokeWidth={1.5} /> Disputes</h2>
        {data.disputes.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-3">No open or in-review disputes.</p>
        ) : (
          <ul className="mt-3 card divide-y divide-[#E5E1D8]" data-testid="dispute-list">
            {data.disputes.map((d) => (
              <li key={d.id} className="py-4 px-4 flex items-center gap-3" data-testid={`queue-dispute-${d.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium truncate">{d.title}</p>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${STATUS_PILL[d.status]}`}>
                      {d.status === "open" ? "Open" : "Under review"}
                    </span>
                    <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">{d.category}</span>
                  </div>
                  <p className="text-xs text-[#5C6B6B] mt-1 truncate">
                    Filed by <strong>{d.filed_by_user?.name || "—"}</strong>, about <strong>{d.against_user?.name || "—"}</strong>
                    {d.assigned_ombudsman_user && <> · assigned to <strong>{d.assigned_ombudsman_user.name}</strong></>}
                  </p>
                  <p className="text-[10px] text-[#5C6B6B]">{new Date(d.created_at).toLocaleString()}</p>
                </div>
                <Link to={`/admin/disputes/${d.id}`} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`open-dispute-${d.id}`}>
                  Review <ExternalLink size={12} strokeWidth={1.5} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10" data-testid="flagged-threads-section">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><AlertTriangle size={16} strokeWidth={1.5} /> Flagged DM threads</h2>
        {data.flagged_threads.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-3">No flagged threads.</p>
        ) : (
          <ul className="mt-3 card divide-y divide-[#E5E1D8]" data-testid="flagged-list">
            {data.flagged_threads.map((t) => {
              const lastFlag = (t.ombudsman_flags || []).slice(-1)[0];
              return (
                <li key={t.id} className="py-4 px-4 flex items-center gap-3" data-testid={`queue-thread-${t.id}`}>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">Thread between {t.participants.length} participants</p>
                    {lastFlag && (
                      <p className="text-xs text-[#5C6B6B] mt-1 truncate">Reason: {lastFlag.reason}</p>
                    )}
                    <p className="text-[10px] text-[#5C6B6B]">Flagged {new Date(t.ombudsman_flagged_at).toLocaleString()}</p>
                  </div>
                  <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">
                    {t.message_count || 0} msgs
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value, testid }) {
  return (
    <div className="card p-4" data-testid={testid}>
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</p>
      <p className="font-serif text-xl mt-1">{value}</p>
    </div>
  );
}
