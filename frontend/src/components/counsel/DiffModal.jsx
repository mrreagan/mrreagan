/**
 * DiffModal — side-by-side (or unified) diff of the working draft vs the
 * released .md. Renders inline comment threads pinned to specific lines,
 * a general-comments panel below the diff, and an admin-only "Release
 * from here" shortcut in the footer.
 */
import React, { useEffect, useMemo, useState } from "react";
import { diffLines } from "diff";
import { toast } from "sonner";
import { ShieldCheck, X as XIcon } from "lucide-react";
import api from "../../lib/api";
import { buildRows, computeDiffStats } from "./diffHelpers";
import {
  ComposeForm, InlineCommentThread, GeneralCommentsPanel,
} from "./CommentPrimitives";

export function DiffModal({ data, onClose, onRelease, currentUser }) {
  const { slug, title, released, working, wd } = data;
  const [mode, setMode] = useState("side"); // "side" | "unified"
  const [comments, setComments] = useState([]);
  const [composeLine, setComposeLine] = useState(null);
  const [composeBody, setComposeBody] = useState("");
  const [composing, setComposing] = useState(false);

  const parts = useMemo(() => diffLines(released || "", working || ""), [released, working]);
  const rows = useMemo(() => buildRows(parts), [parts]);
  const stats = useMemo(() => computeDiffStats(parts), [parts]);

  const loadComments = React.useCallback(async () => {
    if (!slug) return;
    try {
      const r = await api.get(`/legal/working-drafts/${slug}/comments`);
      setComments(r.data || []);
    } catch (e) {
      console.warn("comments load failed", e);
    }
  }, [slug]);

  useEffect(() => { loadComments(); }, [loadComments]);

  const postComment = async (body, lineNumber, parentId) => {
    setComposing(true);
    try {
      await api.post(`/legal/working-drafts/${slug}/comments`, {
        body,
        line_number: lineNumber ?? null,
        side: lineNumber != null ? "working" : "general",
        parent_id: parentId || null,
      });
      setComposeBody("");
      await loadComments();
      toast.success("Comment posted");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Post failed");
    } finally {
      setComposing(false);
    }
  };

  const resolveComment = async (c, resolved) => {
    try {
      await api.post(`/legal/working-drafts/${slug}/comments/${c.id}/resolve`, { resolved });
      await loadComments();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Resolve failed");
    }
  };

  const deleteComment = async (c) => {
    if (!window.confirm("Delete this comment (and any replies)?")) return;
    try {
      await api.delete(`/legal/working-drafts/${slug}/comments/${c.id}`);
      await loadComments();
      toast.success("Comment deleted");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const openCount = comments.filter((c) => !c.resolved).length;
  const totalCount = comments.length;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-stretch justify-center z-[60] p-4" data-testid="diff-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-6xl w-full flex flex-col overflow-hidden">
        <div className="flex items-start justify-between gap-3 p-5 border-b border-[#E5E1D8]">
          <div className="min-w-0">
            <span className="label">Working draft vs. released</span>
            <h2 className="font-serif text-2xl mt-1 truncate">{title}</h2>
            <p className="text-xs text-[#5C6B6B] mt-1">
              <span className="text-[#2E5C46] font-semibold" data-testid="diff-stat-added">+{stats.added} added</span>
              {" · "}
              <span className="text-[#9E3C3C] font-semibold" data-testid="diff-stat-removed">-{stats.removed} removed</span>
              {" · "}
              <span>state <strong>{wd?.state}</strong></span>
              {totalCount > 0 && (
                <>
                  {" · "}
                  <span className="text-[#7A4A1A] font-semibold" data-testid="diff-comment-count">
                    {openCount} open / {totalCount} comment{totalCount === 1 ? "" : "s"}
                  </span>
                </>
              )}
              {" · "}
              <span>last edit by {wd?.last_edited_by_email || wd?.created_by_email}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="rounded-full bg-white/70 p-0.5 flex text-xs">
              <button
                onClick={() => setMode("side")}
                className={`px-3 py-1 rounded-full ${mode === "side" ? "bg-[#0F2424] text-[#FBF3E4]" : "text-[#0F2424]"}`}
                data-testid="diff-mode-side"
              >Side-by-side</button>
              <button
                onClick={() => setMode("unified")}
                className={`px-3 py-1 rounded-full ${mode === "unified" ? "bg-[#0F2424] text-[#FBF3E4]" : "text-[#0F2424]"}`}
                data-testid="diff-mode-unified"
              >Unified</button>
            </div>
            <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="diff-modal-close">
              <XIcon size={20} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto bg-white" data-testid="diff-modal-body">
          {mode === "side" ? (
            <table className="w-full font-mono text-xs" style={{ tableLayout: "fixed" }}>
              <thead className="sticky top-0 bg-[#FAF7F0] text-[#5C6B6B] uppercase tracking-wider text-[10px] z-10">
                <tr>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left border-r border-[#E5E1D8]">Released</th>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left">Working draft</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const lineComments = row.rightNum != null
                    ? comments.filter((c) => c.line_number === row.rightNum)
                    : [];
                  return (
                    <React.Fragment key={i}>
                      <tr className="align-top group">
                        <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.leftClass}`}>{row.leftNum ?? ""}</td>
                        <td className={`px-3 py-0.5 whitespace-pre-wrap break-words border-r border-[#F0EDE3] ${row.leftClass}`}>
                          {row.left ?? ""}
                        </td>
                        <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.rightClass} relative`}>
                          {row.rightNum ?? ""}
                          {row.rightNum != null && (
                            <button
                              onClick={() => setComposeLine(row.rightNum)}
                              className="absolute -left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 bg-[#0F2424] text-[#FBF3E4] rounded-full w-4 h-4 flex items-center justify-center text-[10px] leading-none hover:bg-[#476B6B] transition-opacity"
                              aria-label={`Add comment on line ${row.rightNum}`}
                              data-testid={`diff-add-comment-line-${row.rightNum}`}
                            >+</button>
                          )}
                        </td>
                        <td className={`px-3 py-0.5 whitespace-pre-wrap break-words ${row.rightClass}`}>
                          {row.right ?? ""}
                        </td>
                      </tr>
                      {lineComments.length > 0 && (
                        <tr>
                          <td colSpan={4} className="bg-[#FAF7F0] px-3 py-2 border-y border-[#E5E1D8]">
                            <InlineCommentThread
                              comments={lineComments}
                              allComments={comments}
                              lineNumber={row.rightNum}
                              currentUser={currentUser}
                              onReply={(body, parentId) => postComment(body, row.rightNum, parentId)}
                              onResolve={resolveComment}
                              onDelete={deleteComment}
                            />
                          </td>
                        </tr>
                      )}
                      {composeLine != null && composeLine === row.rightNum && (
                        <tr>
                          <td colSpan={4} className="bg-[#FFF6E3] px-3 py-2 border-y border-[#E5E1D8]">
                            <ComposeForm
                              placeholder={`Ask a question about line ${row.rightNum}…`}
                              value={composeBody}
                              onChange={setComposeBody}
                              onCancel={() => { setComposeLine(null); setComposeBody(""); }}
                              onSubmit={async () => {
                                if (!composeBody.trim()) return;
                                await postComment(composeBody.trim(), row.rightNum, null);
                                setComposeLine(null);
                              }}
                              busy={composing}
                              testidPrefix={`diff-compose-line-${row.rightNum}`}
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="font-mono text-xs">
              {stats.added === 0 && stats.removed === 0 ? (
                <div className="p-8 text-center text-[#5C6B6B]" data-testid="diff-empty-state">
                  Working draft is identical to the released version.
                </div>
              ) : parts.map((p, i) => {
                const bg = p.added ? "bg-[#EAF3EA] text-[#1E4030]"
                  : p.removed ? "bg-[#FBEBEB] text-[#7A2E2E]"
                  : "text-[#0F2424]";
                const prefix = p.added ? "+ " : p.removed ? "- " : "  ";
                return (
                  <div key={i} className={`px-3 py-0.5 whitespace-pre-wrap break-words ${bg}`}>
                    {p.value.replace(/\n$/, "").split("\n").map((l, j) => (
                      <div key={j}>{prefix}{l}</div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}

          <GeneralCommentsPanel
            comments={comments.filter((c) => c.line_number == null)}
            allComments={comments}
            currentUser={currentUser}
            composing={composing}
            composeBody={composeBody}
            setComposeBody={setComposeBody}
            onPost={(body, parentId) => postComment(body, null, parentId)}
            onResolve={resolveComment}
            onDelete={deleteComment}
          />
        </div>

        <div className="p-4 border-t border-[#E5E1D8] flex items-center justify-between bg-[#FAF7F0]">
          <p className="text-xs text-[#5C6B6B]">
            Released body is untouched until admin releases the working draft.
          </p>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn-outline text-sm" data-testid="diff-modal-cancel">
              Close
            </button>
            {onRelease && (
              <button
                onClick={onRelease}
                className="btn-primary text-sm inline-flex items-center gap-1 bg-[#1E4030]"
                data-testid="diff-modal-release"
              >
                <ShieldCheck size={14} /> Release from here
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
