import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { FileText, Plus, CheckCircle, Users, Calendar, X, Sparkles } from "lucide-react";
import api from "../lib/api";

/* AdminAgreements — /admin/legal/agreements
 *
 * One-stop shop for publishing and tracking universal indemnification
 * agreement versions. Replaces the "raw API call" workflow that previously
 * required a curl POST or DB write.
 *
 * Three sub-views:
 *   1. Version list (active version highlighted, signature counts, "% of
 *      active partners signed")
 *   2. Draft & publish modal (markdown body + summary of changes + version
 *      string). "Seed from birthright v2.0 draft" pulls the curated default
 *      so the admin isn't authoring from scratch.
 *   3. Signature ledger per version (who signed, when, sticky modal)
 */
export default function AdminAgreements() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [draftOpen, setDraftOpen] = useState(false);
  const [ledgerVersionId, setLedgerVersionId] = useState(null);

  // Draft form state
  const [version, setVersion] = useState("2.0");
  const [summary, setSummary] = useState("");
  const [body, setBody] = useState("");
  const [publishing, setPublishing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/legal/indemnification/versions");
      setData(r.data);
    } catch {
      toast.error("Couldn't load versions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const seedFromV2 = async () => {
    try {
      const r = await api.get("/legal/indemnification/default-v2-draft");
      setVersion(r.data.version);
      setSummary(r.data.summary_of_changes);
      setBody(r.data.body);
      toast.success("Seeded with birthright v2.0 starter content");
    } catch {
      toast.error("Couldn't load default v2 draft");
    }
  };

  const publish = async () => {
    if (!version.trim() || body.trim().length < 50) {
      toast.error("Version + a real body (≥ 50 chars) are required");
      return;
    }
    if (!window.confirm(
      `Activate v${version.trim()}? This will:\n` +
      `  • Deactivate any prior active version\n` +
      `  • Require every active partner to re-sign\n` +
      `  • Send a notification email to all active partners\n\n` +
      `Continue?`
    )) return;
    setPublishing(true);
    try {
      await api.post("/legal/indemnification/versions", {
        version: version.trim(),
        body: body.trim(),
        summary_of_changes: summary.trim(),
      });
      toast.success(`v${version.trim()} published & emails dispatched`);
      setDraftOpen(false);
      setVersion(""); setSummary(""); setBody("");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Publish failed");
    } finally {
      setPublishing(false);
    }
  };

  if (loading) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</p>;
  const versions = data?.versions || [];
  const activePartnerCount = data?.active_partner_count || 0;
  const activeV = versions.find((v) => v.active);

  return (
    <div className="container-page py-12" data-testid="admin-agreements-page">
      <span className="label">Admin · Legal</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <FileText size={26} strokeWidth={1.2} /> Partnership agreements
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Publish, activate, and audit the universal indemnification agreement. The
        active version gates partner write-side features (publishing artifacts,
        purchasing featured slots, generating AI Studio drafts, updating
        payout). Reads are never gated.
      </p>

      <div className="grid md:grid-cols-3 gap-4 mt-6">
        <SummaryTile label="Active version" value={activeV ? `v${activeV.version}` : "—"} testid="tile-active" />
        <SummaryTile label="Active partners" value={activePartnerCount} testid="tile-partners" />
        <SummaryTile
          label="% of partners signed (active version)"
          value={
            activeV
              ? (activePartnerCount > 0
                  ? `${Math.round((activeV.signature_count / activePartnerCount) * 100)}%`
                  : "—")
              : "—"
          }
          testid="tile-signed-pct"
        />
      </div>

      <div className="flex justify-end mt-6">
        <button
          onClick={() => setDraftOpen(true)}
          className="btn-primary text-xs inline-flex items-center gap-1"
          data-testid="open-draft-version"
        >
          <Plus size={12} strokeWidth={2} /> Draft &amp; publish new version
        </button>
      </div>

      <h2 className="font-serif text-xl mt-8 mb-3">All versions</h2>
      {versions.length === 0 ? (
        <p className="text-sm text-[#5C6B6B] italic">No versions yet. Publish the first one to start gating partner write-features.</p>
      ) : (
        <div className="space-y-3" data-testid="versions-list">
          {versions.map((v) => {
            const pct = activePartnerCount > 0 ? Math.round((v.signature_count / activePartnerCount) * 100) : 0;
            return (
              <div key={v.id} className={`card p-4 ${v.active ? "ring-2 ring-[#476B6B]" : ""}`} data-testid={`version-row-${v.id}`}>
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <p className="font-serif text-lg">v{v.version}</p>
                      {v.active && (
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#476B6B] text-white inline-flex items-center gap-1">
                          <CheckCircle size={10} strokeWidth={2} /> Active
                        </span>
                      )}
                      <span className="text-[10px] text-[#5C6B6B] inline-flex items-center gap-1">
                        <Calendar size={10} strokeWidth={1.7} />
                        {v.activated_at?.slice(0, 10)}
                      </span>
                    </div>
                    {v.summary_of_changes && (
                      <p className="text-xs text-[#476B6B] mt-1 leading-relaxed">{v.summary_of_changes}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-[#5C6B6B] flex-wrap">
                      <span className="inline-flex items-center gap-1">
                        <Users size={11} strokeWidth={1.7} /> {v.signature_count} signature{v.signature_count === 1 ? "" : "s"}
                      </span>
                      {v.active && activePartnerCount > 0 && (
                        <span>· {pct}% of active partners signed</span>
                      )}
                    </div>
                    {v.active && activePartnerCount > 0 && (
                      <div className="mt-2 h-1.5 rounded-full bg-[#FAF8F5] overflow-hidden max-w-md">
                        <div className="h-full bg-[#476B6B] transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setLedgerVersionId(v.id)}
                    className="btn-outline text-xs"
                    data-testid={`version-ledger-${v.id}`}
                  >
                    View signers
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {draftOpen && (
        <DraftModal
          version={version} setVersion={setVersion}
          summary={summary} setSummary={setSummary}
          body={body} setBody={setBody}
          onSeedFromV2={seedFromV2}
          onClose={() => setDraftOpen(false)}
          onPublish={publish}
          publishing={publishing}
        />
      )}

      {ledgerVersionId && (
        <SignatureLedgerModal
          versionId={ledgerVersionId}
          onClose={() => setLedgerVersionId(null)}
        />
      )}
    </div>
  );
}

function SummaryTile({ label, value, testid }) {
  return (
    <div className="card p-5" data-testid={testid}>
      <p className="label">{label}</p>
      <p className="font-serif text-3xl mt-2">{value}</p>
    </div>
  );
}

function DraftModal({ version, setVersion, summary, setSummary, body, setBody, onSeedFromV2, onClose, onPublish, publishing }) {
  return (
    <div className="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-2xl max-w-3xl w-full p-6 my-8" onClick={(e) => e.stopPropagation()} data-testid="draft-version-modal">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-serif text-xl inline-flex items-center gap-2">
            <Plus size={18} strokeWidth={1.5} /> Draft &amp; publish new version
          </h3>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        <button
          onClick={onSeedFromV2}
          className="btn-outline text-xs inline-flex items-center gap-1 mb-3 !border-[#C9A961] !text-[#8B7128]"
          data-testid="seed-from-v2"
        >
          <Sparkles size={11} strokeWidth={1.5} /> Seed from birthright v2.0 starter
        </button>

        <div className="grid sm:grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Version string</label>
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              className="input-field text-sm w-full font-mono"
              placeholder="2.0"
              data-testid="draft-version-input"
            />
          </div>
        </div>
        <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Summary of changes</label>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={3}
          className="input-field text-sm w-full"
          placeholder="One sentence each on what changed. Shown to partners in the banner + email."
          data-testid="draft-summary"
        />
        <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-3 mb-1">Body (Markdown)</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={16}
          className="input-field text-sm w-full font-mono leading-relaxed"
          placeholder="Full agreement text. Markdown is rendered on /legal/agreement."
          data-testid="draft-body"
        />
        <p className="text-[10px] text-[#5C6B6B] mt-1">
          {body.length} characters · Publishing will deactivate the current version and email every active partner.
        </p>
        <div className="flex gap-2 mt-5 justify-end">
          <button onClick={onClose} className="btn-outline text-xs" data-testid="draft-cancel">Cancel</button>
          <button onClick={onPublish} disabled={publishing} className="btn-primary text-xs !bg-[#9E3C3C] hover:!bg-[#7E2C2C]" data-testid="draft-publish">
            {publishing ? "Publishing…" : `Publish v${version || "?"}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function SignatureLedgerModal({ versionId, onClose }) {
  const [rows, setRows] = useState(null);

  useEffect(() => {
    api.get(`/legal/indemnification/signatures?version_id=${versionId}`)
      .then((r) => setRows(r.data))
      .catch(() => setRows([]));
  }, [versionId]);

  return (
    <div className="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()} data-testid="signature-ledger-modal">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-serif text-xl">Signature ledger</h3>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
        {rows === null ? (
          <p className="text-sm text-[#5C6B6B]">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] italic" data-testid="ledger-empty">No signatures yet for this version.</p>
        ) : (
          <table className="w-full text-sm" data-testid="ledger-table">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                <th className="text-left px-2 py-1.5">User</th>
                <th className="text-left px-2 py-1.5">Signed at</th>
                <th className="text-left px-2 py-1.5">IP</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-[#E5E1D8]">
                  <td className="px-2 py-1.5 text-xs">{r.user_email || r.user_id?.slice(0, 8)}</td>
                  <td className="px-2 py-1.5 text-xs">{r.signed_at?.replace("T", " ").slice(0, 16)}</td>
                  <td className="px-2 py-1.5 text-[10px] font-mono text-[#5C6B6B]">{r.ip_address || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
