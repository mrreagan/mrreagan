import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Scale, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";

export default function AgreementPage() {
  const [version, setVersion] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      api.get("/legal/indemnification/active"),
      api.get("/legal/indemnification/my-status"),
    ]).then(([v, s]) => { setVersion(v.data); setStatus(s.data); })
      .catch(() => toast.error("Could not load agreement"));
  }, []);

  const sign = async () => {
    if (!version) return;
    setBusy(true);
    try {
      await api.post("/legal/indemnification/sign", { version_id: version.id });
      toast.success("Thank you — agreement accepted.");
      setStatus({ ...status, signed: true });
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not sign");
    } finally {
      setBusy(false);
    }
  };

  if (!version) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</p>;
  const alreadySigned = !!status?.signed;

  return (
    <div className="container-page py-12" data-testid="agreement-page">
      <span className="label">Legal · Indemnification</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Scale size={28} strokeWidth={1.2} /> Agreement v{version.version}
      </h1>
      <div className="divider-flame" />
      <div className="card p-6 max-w-3xl whitespace-pre-wrap text-sm leading-relaxed font-sans" data-testid="agreement-body">
        {version.body}
      </div>

      {version.summary_of_changes && (
        <div className="card p-4 mt-4 max-w-3xl bg-[#FAF8F5]" data-testid="agreement-changes">
          <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">What changed</p>
          <p className="text-xs mt-1">{version.summary_of_changes}</p>
        </div>
      )}

      <div className="mt-6 flex items-center gap-3 flex-wrap" data-testid="agreement-actions">
        {alreadySigned ? (
          <p className="text-sm text-[#2E5C46] inline-flex items-center gap-2" data-testid="agreement-already-signed">
            <CheckCircle2 size={16} strokeWidth={1.5} /> You accepted this version on{" "}
            {status?.signed_at && new Date(status.signed_at).toLocaleDateString()}.
          </p>
        ) : (
          <button onClick={sign} disabled={busy} className="btn-primary text-sm" data-testid="agreement-accept">
            {busy ? "Saving…" : `I accept agreement v${version.version}`}
          </button>
        )}
        <button onClick={() => navigate(-1)} className="btn-outline text-xs">Back</button>
      </div>
    </div>
  );
}
