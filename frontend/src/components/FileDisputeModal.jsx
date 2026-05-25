/** Modal to file a dispute against another user, optionally linked to a thread or transaction. */
import React, { useState } from "react";
import { toast } from "sonner";
import { Scale, X } from "lucide-react";
import api from "../lib/api";

const CATEGORIES = [
  { value: "payment", label: "Payment / refund" },
  { value: "conduct", label: "Conduct / boundary violation" },
  { value: "content", label: "Content / moderation appeal" },
  { value: "other",   label: "Other" },
];

export default function FileDisputeModal({
  open, onClose, againstUserId, againstUserName,
  threadId, transactionId, onFiled,
}) {
  const [category, setCategory] = useState("conduct");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  const submit = async () => {
    if (title.trim().length < 5) { toast.error("Title must be at least 5 characters"); return; }
    if (description.trim().length < 20) { toast.error("Description must be at least 20 characters"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/disputes", {
        against_user_id: againstUserId,
        category,
        title: title.trim(),
        description: description.trim(),
        thread_id: threadId || undefined,
        transaction_id: transactionId || undefined,
      });
      toast.success("Dispute filed. The ombudsman will review.");
      if (onFiled) onFiled(data);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not file dispute");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="file-dispute-modal">
      <div className="bg-white rounded shadow-xl max-w-xl w-full p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-serif text-xl inline-flex items-center gap-2">
            <Scale size={18} strokeWidth={1.5} className="text-[#C9A961]" /> File a dispute
          </h3>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
        <p className="text-sm text-[#5C6B6B]">
          {againstUserName ? `Filing against ${againstUserName}.` : "Filing against the other party."} The ombudsman reviews
          disputes confidentially. Please give them what they need to investigate.
        </p>

        <label className="block mt-4 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Category</label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="input-field text-sm w-full"
          data-testid="dispute-category"
        >
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>

        <label className="block mt-3 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Title (short summary)</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="input-field text-sm w-full"
          placeholder="e.g. Workshop refund not issued"
          maxLength={200}
          data-testid="dispute-title"
        />

        <label className="block mt-3 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">What happened?</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          className="input-field text-sm w-full"
          placeholder="Be specific: dates, amounts, what was promised, what happened. The ombudsman can request more later."
          maxLength={8000}
          data-testid="dispute-description"
        />

        {threadId && (
          <p className="text-[10px] text-[#5C6B6B] mt-3">
            This dispute is linked to the current conversation. The ombudsman can review the thread on flag.
          </p>
        )}
        {transactionId && (
          <p className="text-[10px] text-[#5C6B6B] mt-1">
            This dispute is linked to transaction <code className="text-[10px]">{transactionId}</code>.
          </p>
        )}

        <div className="flex gap-2 mt-5">
          <button onClick={submit} disabled={busy} className="btn-primary text-xs" data-testid="dispute-submit">
            {busy ? "Filing…" : "File dispute"}
          </button>
          <button onClick={onClose} className="btn-outline text-xs">Cancel</button>
        </div>
      </div>
    </div>
  );
}
