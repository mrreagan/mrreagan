/**
 * HistoryModal — release timeline for one legal doc + admin rollback.
 * Contains the nested RollbackPreviewModal for diff-before-confirm UX.
 */
import React, { useEffect, useMemo, useState } from "react";
import { diffLines } from "diff";
import { toast } from "sonner";
import { X as XIcon, Undo2 } from "lucide-react";
import api from "../../lib/api";
import { buildRows, computeDiffStats } from "./diffHelpers";

export function HistoryModal({ data, isAdmin, onClose, onRolledBack }) {
  const { slug, title } = data;
  const [state, setState] = useState({ loading: true, data: null });
  const [limit, setLimit] = useState(5);
  const [busy, setBusy] = useState(null);
  const [previewTarget, setPreviewTarget] = useState(null);

  const load = React.useCallback(async (n) => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const r = await api.get(`/legal/history-timeline/${slug}`, { params: { limit: n } });
      setState({ loading: false, data: r.data });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load history");
      setState({ loading: false, data: null });
    }
  }, [slug]);

  useEffect(() => { load(limit); }, [load, limit]);

  const openPreview = async (rat) => {
    if (!isAdmin) return;
    setBusy(rat.id);
    try {
      const r = await api.get(`/legal/history/${slug}/rollback-preview/${rat.id}`);
      setPreviewTarget({ rat, preview: r.data, reason: "" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load rollback preview");
    } finally {
      setBusy(null);
    }
  };

  const confirmRollback = async () => {
    if (!previewTarget) return;
    const { rat, reason } = previewTarget;
    setBusy(rat.id);
    try {
      const r = await api.post(`/legal/history/${slug}/rollback/${rat.id}`, { reason });
      toast.success(`Rolled back to v${rat.version} · new version v${r.data.version}`);
      setPreviewTarget(null);
      await onRolledBack();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Rollback failed");
    } finally {
      setBusy(null);
    }
  };

  const d = state.data;
  const total = d?.total_versions || 0;
  const showingAll = limit >= total;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60] p-4" data-testid="history-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-2xl w-full flex flex-col overflow-hidden max-h-[85vh]">
        <div className="p-5 border-b border-[#E5E1D8] flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="label">Release history</span>
            <h2 className="font-serif text-2xl mt-1 truncate">{title}</h2>
            <p className="text-xs text-[#5C6B6B] mt-1" data-testid="history-total">
              {state.loading ? "Loading…" : (
                total === 0 ? "No versions released yet."
                : <>Showing <strong>{Math.min(limit, total)}</strong> of <strong>{total}</strong> total release{total === 1 ? "" : "s"} · current v<strong>{d?.current_version}</strong></>
              )}
            </p>
          </div>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="history-modal-close">
            <XIcon size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-5 space-y-3" data-testid="history-modal-body">
          {state.loading && <p className="text-sm text-[#5C6B6B]">Loading…</p>}
          {!state.loading && total === 0 && (
            <div className="text-sm text-[#5C6B6B] p-6 text-center" data-testid="history-empty">
              This doc hasn&apos;t been released yet. Once an admin releases a working draft, the version will appear here.
            </div>
          )}
          {(d?.versions || []).map((v, idx) => {
            const cs = v.change_summary || {};
            const isCurrent = idx === 0;
            return (
              <div
                key={v.id}
                className={`rounded-lg border p-4 ${isCurrent ? "border-[#1E4030] bg-white" : "border-[#E5E1D8] bg-white/60"}`}
                data-testid={`history-row-${v.version}`}
                data-ratification-id={v.id}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <strong className="font-serif text-lg text-[#0F2424]">v{v.version}</strong>
                      {isCurrent && (
                        <span className="text-[10px] uppercase tracking-wider bg-[#1E4030] text-[#FBF3E4] rounded-full px-2 py-0.5 font-semibold">
                          Current
                        </span>
                      )}
                      {v.rolled_back_from_ratification_id && (
                        <span className="text-[10px] uppercase tracking-wider bg-[#F5E6D6] text-[#7A5A1A] rounded-full px-2 py-0.5 font-semibold inline-flex items-center gap-1">
                          <Undo2 size={10} /> Rollback from v{cs.rolled_back_from_version || "?"}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#5C6B6B] mt-1">
                      {new Date(v.ratified_at).toLocaleString()} · by <strong className="text-[#0F2424]">{v.ratified_by}</strong>
                    </p>
                    {v.notes && (
                      <p className="text-sm text-[#0F2424] mt-2 leading-relaxed" data-testid={`history-row-${v.version}-notes`}>
                        {v.notes}
                      </p>
                    )}
                    {cs.edits > 0 && (
                      <p className="text-xs text-[#5C6B6B] mt-2">
                        <strong>{cs.edits}</strong> edit{cs.edits === 1 ? "" : "s"} by {(cs.authors || []).join(", ") || "counsel"}
                        {cs.actions && Object.keys(cs.actions).length > 0 && (
                          <>
                            {" · "}
                            {Object.entries(cs.actions).map(([a, n], i) => (
                              <span key={a}>{i > 0 && ", "}{n} {a.replace(/_/g, " ")}</span>
                            ))}
                          </>
                        )}
                      </p>
                    )}
                  </div>
                  {isAdmin && !isCurrent && v.can_rollback && (
                    <button
                      onClick={() => openPreview(v)}
                      disabled={busy === v.id}
                      className="btn-outline text-xs inline-flex items-center gap-1 text-[#7A5A1A] border-[#7A5A1A] shrink-0"
                      data-testid={`history-row-${v.version}-rollback`}
                    >
                      <Undo2 size={12} /> {busy === v.id ? "Loading…" : "Rollback"}
                    </button>
                  )}
                  {isAdmin && !isCurrent && !v.can_rollback && (
                    <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B] shrink-0" title="No content snapshot on record">
                      No snapshot
                    </span>
                  )}
                </div>
              </div>
            );
          })}
          {!state.loading && !showingAll && total > 0 && (
            <button
              onClick={() => setLimit((n) => Math.min(n + 5, total))}
              className="text-xs uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold mt-2"
              data-testid="history-show-more"
            >
              Show {Math.min(5, total - limit)} more →
            </button>
          )}
        </div>

        <div className="p-4 border-t border-[#E5E1D8] flex items-center justify-between bg-[#FAF7F0]">
          <p className="text-xs text-[#5C6B6B]">
            Rollback creates a new release with the older content. Full history is preserved.
          </p>
          <button onClick={onClose} className="btn-outline text-sm" data-testid="history-modal-cancel">
            Close
          </button>
        </div>
      </div>
      {previewTarget && (
        <RollbackPreviewModal
          data={previewTarget}
          slugTitle={title}
          onCancel={() => setPreviewTarget(null)}
          onChangeReason={(reason) => setPreviewTarget((p) => ({ ...p, reason }))}
          onConfirm={confirmRollback}
          busy={busy === previewTarget.rat.id}
        />
      )}
    </div>
  );
}

// -------- Rollback preview modal (nested under HistoryModal) --------
function RollbackPreviewModal({ data, slugTitle, onCancel, onChangeReason, onConfirm, busy }) {
  const { rat, preview, reason } = data;
  const parts = useMemo(
    () => diffLines(preview?.current_md || "", preview?.target_md || ""),
    [preview],
  );
  const rows = useMemo(() => buildRows(parts), [parts]);
  const stats = useMemo(() => computeDiffStats(parts), [parts]);
  const noChange = stats.added === 0 && stats.removed === 0;
  return (
    <div className="fixed inset-0 bg-black/60 flex items-stretch justify-center z-[70] p-4" data-testid="rollback-preview-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-5xl w-full flex flex-col overflow-hidden max-h-[90vh]">
        <div className="p-5 border-b border-[#E5E1D8] flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="label">Rollback preview · {slugTitle}</span>
            <h2 className="font-serif text-2xl mt-1">
              Restore v{preview.target_version}
              <span className="text-[#5C6B6B] text-base ml-2">(currently v{preview.current_version})</span>
            </h2>
            <p className="text-xs text-[#5C6B6B] mt-1">
              Target ratified <strong>{new Date(preview.target_ratified_at).toLocaleString()}</strong> by <strong>{preview.target_ratified_by}</strong>.
              {noChange ? (
                <> · <span className="text-[#7A5A1A] font-semibold">No textual change</span></>
              ) : (
                <>
                  {" "}<span className="text-[#2E5C46] font-semibold">+{stats.added} to add</span>
                  {" · "}<span className="text-[#9E3C3C] font-semibold">-{stats.removed} to remove</span>
                </>
              )}
            </p>
          </div>
          <button onClick={onCancel} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="rollback-preview-close">
            <XIcon size={20} />
          </button>
        </div>

        <div className={noChange ? "bg-white" : "flex-1 overflow-auto bg-white"} data-testid="rollback-preview-body">
          {noChange ? (
            <div className="p-8 text-center text-[#5C6B6B]" data-testid="rollback-preview-empty">
              This rollback would produce no textual change — target and current are already identical.
            </div>
          ) : (
            <table className="w-full font-mono text-xs" style={{ tableLayout: "fixed" }}>
              <thead className="sticky top-0 bg-[#FAF7F0] text-[#5C6B6B] uppercase tracking-wider text-[10px] z-10">
                <tr>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left border-r border-[#E5E1D8]">Current v{preview.current_version}</th>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left">Target v{preview.target_version} (will be restored)</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="align-top">
                    <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.leftClass}`}>{row.leftNum ?? ""}</td>
                    <td className={`px-3 py-0.5 whitespace-pre-wrap break-words border-r border-[#F0EDE3] ${row.leftClass}`}>
                      {row.left ?? ""}
                    </td>
                    <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.rightClass}`}>{row.rightNum ?? ""}</td>
                    <td className={`px-3 py-0.5 whitespace-pre-wrap break-words ${row.rightClass}`}>
                      {row.right ?? ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="p-4 border-t border-[#E5E1D8] bg-[#FAF7F0] space-y-3">
          <div>
            <label className="label block mb-1">Reason (optional but recommended)</label>
            <textarea
              value={reason}
              onChange={(e) => onChangeReason(e.target.value)}
              placeholder="Why are you rolling back? This is stored in the new release's notes."
              className="input input-bordered w-full text-sm min-h-[60px]"
              data-testid="rollback-preview-reason"
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-[#5C6B6B]">
              Rolling back creates a new ratification with the older content. Any open working draft will be auto-discarded.
            </p>
            <div className="flex gap-2 shrink-0">
              <button onClick={onCancel} className="btn-outline text-sm" data-testid="rollback-preview-cancel">
                Cancel
              </button>
              <button
                onClick={onConfirm}
                disabled={busy || noChange}
                className="btn-primary text-sm inline-flex items-center gap-1 bg-[#7A5A1A] disabled:opacity-50"
                data-testid="rollback-preview-confirm"
                title={noChange ? "Target and current are identical — no rollback needed." : undefined}
              >
                <Undo2 size={14} /> {busy ? "Rolling back…" : `Confirm rollback to v${rat.version}`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
