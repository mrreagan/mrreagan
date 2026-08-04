/**
 * CounselReviewChecklist — visible to counsel (readonly_admin) and full admin.
 *
 * Every legal draft, the counsel briefing, and the ISTV memo appear as rows
 * with two checkboxes:
 *   - Manual  — counsel initials + optional notes; durable sign-off record
 *   - Auto    — read-only badge sourced from the counsel activity log,
 *               indicating whether the document URL has actually been opened
 *
 * URL: /admin/counsel-review
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Check, Circle, Download, RefreshCw } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

function ReviewRow({ item, onSaved }) {
  const [checked, setChecked] = useState(item.manual_reviewed);
  const [initials, setInitials] = useState(item.manual_initials || "");
  const [notes, setNotes] = useState(item.notes || "");
  const [saving, setSaving] = useState(false);
  const dirty =
    checked !== item.manual_reviewed ||
    (initials || "") !== (item.manual_initials || "") ||
    (notes || "") !== (item.notes || "");

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/counsel/review-status/${item.slug}`, {
        reviewed: checked,
        initials: initials || null,
        notes: notes || null,
      });
      toast.success(checked ? "Marked reviewed" : "Mark cleared");
      onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="border-b border-[#E8E4DC] align-top" data-testid={`review-row-${item.slug}`}>
      <td className="p-3">
        <div className="font-semibold text-[#0F2424] text-sm">{item.display_name}</div>
        <div className="text-xs text-[#5C6B6B] font-mono mt-0.5">{item.slug}</div>
        <div className="text-[10px] uppercase tracking-wide text-[#8B7128] mt-1">{item.category}</div>
      </td>

      {/* Manual checkbox column */}
      <td className="p-3 w-56">
        <label className="flex items-start gap-2 cursor-pointer" data-testid={`manual-check-${item.slug}`}>
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            className="mt-1 h-4 w-4 rounded border-2 border-[#0F2424] accent-[#C9A961]"
          />
          <div className="flex-1">
            <input
              type="text"
              placeholder="Initials"
              maxLength={8}
              value={initials}
              onChange={(e) => setInitials(e.target.value.toUpperCase())}
              className="input-field text-xs py-1 w-full font-mono uppercase tracking-widest"
              data-testid={`manual-initials-${item.slug}`}
            />
            {item.manual_reviewed_at && (
              <div className="text-[10px] text-[#5C6B6B] mt-1">
                {new Date(item.manual_reviewed_at).toLocaleDateString()} · {item.reviewer_email || "?"}
              </div>
            )}
          </div>
        </label>
      </td>

      {/* Auto badge column */}
      <td className="p-3 w-40">
        {item.auto_visited ? (
          <div className="text-xs" data-testid={`auto-badge-visited-${item.slug}`}>
            <span className="inline-flex items-center gap-1 bg-[#E5F0E8] text-[#01784E] px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold">
              <Check size={10} strokeWidth={2.5} /> Opened
            </span>
            <div className="text-[10px] text-[#5C6B6B] mt-1">
              {item.auto_visit_count} visit{item.auto_visit_count === 1 ? "" : "s"}
              {item.auto_last_visited_at && (
                <div className="mt-0.5">
                  last: {new Date(item.auto_last_visited_at).toLocaleString()}
                </div>
              )}
            </div>
          </div>
        ) : (
          <span
            className="inline-flex items-center gap-1 bg-[#F4F1EA] text-[#5C6B6B] px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold"
            data-testid={`auto-badge-unopened-${item.slug}`}
          >
            <Circle size={10} strokeWidth={2} /> Not opened
          </span>
        )}
      </td>

      {/* Notes column */}
      <td className="p-3">
        <textarea
          rows={2}
          placeholder="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="input-field text-xs py-1 w-full"
          data-testid={`review-notes-${item.slug}`}
        />
      </td>

      {/* Actions */}
      <td className="p-3 w-40 whitespace-nowrap">
        <div className="flex flex-col gap-1">
          <a
            href={item.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-outline text-xs py-1 px-2 inline-flex items-center justify-center gap-1"
            data-testid={`download-${item.slug}`}
          >
            <Download size={11} strokeWidth={1.8} /> Open
          </a>
          <button
            onClick={save}
            disabled={saving || !dirty}
            className={`text-xs py-1 px-2 rounded border font-semibold ${
              dirty
                ? "bg-[#C9A961] border-[#C9A961] text-[#0F2424] hover:bg-[#D4B677]"
                : "bg-[#EDEDED] border-[#EDEDED] text-[#9CA9A9] cursor-not-allowed"
            }`}
            data-testid={`save-${item.slug}`}
          >
            {saving ? "…" : "Save"}
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function CounselReviewChecklist() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all"); // all | pending | reviewed | opened | unopened

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/counsel/review-status");
      setItems(r.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load review checklist");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const counts = useMemo(() => {
    const total = items.length;
    const reviewed = items.filter((i) => i.manual_reviewed).length;
    const opened = items.filter((i) => i.auto_visited).length;
    const unopened = items.filter((i) => !i.auto_visited).length;
    return { total, reviewed, pending: total - reviewed, opened, unopened };
  }, [items]);

  const visible = useMemo(() => {
    if (filter === "all") return items;
    if (filter === "pending") return items.filter((i) => !i.manual_reviewed);
    if (filter === "reviewed") return items.filter((i) => i.manual_reviewed);
    if (filter === "opened") return items.filter((i) => i.auto_visited);
    if (filter === "unopened") return items.filter((i) => !i.auto_visited);
    return items;
  }, [items, filter]);

  return (
    <div className="container-page py-12" data-testid="counsel-review-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-4">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="label">Counsel review</span>
          <h1 className="editorial-h1 mt-1">Legal Document Review Checklist</h1>
        </div>
        <button onClick={load} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="refresh-btn">
          <RefreshCw size={12} strokeWidth={1.5} /> Refresh
        </button>
      </div>

      <div className="divider-flame" />

      <p className="text-sm text-[#5C6B6B] max-w-3xl leading-relaxed mt-4">
        Every legal draft plus the counsel briefing. Two checks per document:{" "}
        <strong>Manual</strong> — a checkbox for counsel (or admin) to initial as
        reviewed; and <strong>Auto</strong> — an automatic indicator sourced from
        the counsel activity log, showing whether the document URL has actually
        been opened. Both views are visible to counsel and admin.
      </p>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap gap-2" data-testid="review-filters">
        {[
          ["all", `All · ${counts.total}`],
          ["pending", `Pending manual · ${counts.pending}`],
          ["reviewed", `Manually reviewed · ${counts.reviewed}`],
          ["opened", `Auto-opened · ${counts.opened}`],
          ["unopened", `Not opened · ${counts.unopened}`],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`text-xs px-3 py-1 rounded-full border ${
              filter === key
                ? "bg-[#0F2424] border-[#0F2424] text-white"
                : "bg-white border-[#E8E4DC] text-[#5C6B6B] hover:border-[#0F2424]"
            }`}
            data-testid={`filter-${key}`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-[#5C6B6B] mt-8">Loading…</p>
      ) : (
        <div className="mt-6 card overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-[#F4F1EA] text-xs uppercase tracking-wide text-[#5C6B6B]">
              <tr>
                <th className="p-3">Document</th>
                <th className="p-3">Manual review</th>
                <th className="p-3">Auto (opened?)</th>
                <th className="p-3">Notes</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => <ReviewRow key={item.slug} item={item} onSaved={load} />)}
              {visible.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-sm text-[#5C6B6B] text-center">No documents match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
