import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ShieldCheck, FileText, CheckCircle2 } from "lucide-react";

function fmt(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

export default function IndemnificationPage() {
  const { user } = useAuth();
  const [active, setActive] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState(false);

  const loadAll = () => {
    api.get("/legal/indemnification/active").then((r) => setActive(r.data)).catch(() => {});
    if (user) {
      api.get("/legal/indemnification/my-status").then((r) => setStatus(r.data)).catch(() => {});
    }
  };
  useEffect(loadAll, [user]);

  const sign = async () => {
    if (!accepted) { toast.error("Please tick the box to confirm you've read it."); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/legal/indemnification/sign", {});
      if (data.already_signed) {
        toast.info(`You signed v${data.version} on ${fmt(data.signed_at)}`);
      } else {
        toast.success(`Signed v${data.version}`);
      }
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not sign");
    } finally { setBusy(false); }
  };

  return (
    <div className="container-page py-12 max-w-3xl" data-testid="indemnification-page">
      <span className="label inline-flex items-center gap-1"><FileText size={11} strokeWidth={1.5} /> Legal</span>
      <h1 className="editorial-h1 mt-2">Universal indemnification</h1>
      <div className="divider-flame" />

      {!active ? (
        <p className="text-sm text-[#5C6B6B]">Loading…</p>
      ) : (
        <>
          <div className="flex items-center justify-between flex-wrap gap-2 mt-2">
            <p className="text-sm text-[#5C6B6B]">
              Active version: <span className="font-medium text-[#1A2424]">v{active.version}</span>
              {" · "} Activated {fmt(active.activated_at)}
            </p>
            {status?.signed ? (
              <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#2E5C46] border border-[#2E5C46]/30 px-2 py-1 rounded-full" data-testid="signed-badge">
                <CheckCircle2 size={11} strokeWidth={2} /> Signed v{status.active_version?.version} on {fmt(status.signed_at)}
              </span>
            ) : user ? (
              <span className="text-[10px] uppercase tracking-wider text-[#B86A5C]" data-testid="not-signed-label">
                Not yet signed
              </span>
            ) : null}
          </div>

          <article
            className="prose prose-sm max-w-none mt-6 bg-[#FAF8F5] border border-[#E5E1D8] p-6 rounded whitespace-pre-wrap font-sans text-sm"
            data-testid="indemnification-body"
          >
            {active.body}
          </article>

          {active.summary_of_changes && (
            <p className="text-xs text-[#5C6B6B] mt-3 italic">What's new in this version: {active.summary_of_changes}</p>
          )}

          {user && !status?.signed && (
            <div className="card p-5 mt-6" data-testid="sign-block">
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                  data-testid="accept-checkbox"
                />
                <span>
                  I have read and understood the universal indemnification agreement (v{active.version}). I accept these terms as a participant or partner with birthright Foundation.
                </span>
              </label>
              <button onClick={sign} disabled={busy || !accepted} className="btn-primary mt-4 inline-flex items-center gap-2" data-testid="sign-btn">
                <ShieldCheck size={14} strokeWidth={1.5} />
                {busy ? "Signing…" : "Sign v" + active.version}
              </button>
            </div>
          )}

          {!user && (
            <p className="text-sm text-[#5C6B6B] mt-6">Sign in to record your acceptance.</p>
          )}
        </>
      )}
    </div>
  );
}
