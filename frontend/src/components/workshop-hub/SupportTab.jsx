import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../../lib/api";

function StatusBadge({ status }) {
  const styles = status === "resolved"
    ? "bg-[#2E5C46]/10 text-[#2E5C46]"
    : "bg-[#C9A961]/15 text-[#C9A961]";
  return (
    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${styles}`}>
      {status}
    </span>
  );
}

function SupportItem({ item }) {
  return (
    <div className="card p-5" data-testid={`support-${item.id}`}>
      <div className="flex items-center justify-between">
        <p className="font-medium">{item.subject}</p>
        <StatusBadge status={item.status} />
      </div>
      <p className="text-sm text-[#5C6B6B] mt-2 whitespace-pre-line">{item.content}</p>
      {item.response && (
        <div className="mt-3 border-t border-[#E5E1D8] pt-3 text-sm">
          <p className="text-xs label">Reply from {item.responded_by}</p>
          <p className="text-[#1A2424] mt-1 whitespace-pre-line">{item.response}</p>
        </div>
      )}
    </div>
  );
}

function NewSupportForm({ form, setForm, onSubmit }) {
  return (
    <div className="card p-5 h-fit sticky top-24">
      <span className="label">New request</span>
      <form onSubmit={onSubmit} className="mt-3 space-y-3">
        <input
          required
          value={form.subject}
          onChange={(e) => setForm({ ...form, subject: e.target.value })}
          placeholder="Subject"
          className="input-field"
          data-testid="support-subject"
        />
        <textarea
          required
          rows={5}
          value={form.content}
          onChange={(e) => setForm({ ...form, content: e.target.value })}
          placeholder="How can we help?"
          className="input-field resize-none"
          data-testid="support-content"
        />
        <select
          value={form.urgency}
          onChange={(e) => setForm({ ...form, urgency: e.target.value })}
          className="input-field"
          data-testid="support-urgency"
        >
          <option value="low">Low urgency</option>
          <option value="normal">Normal</option>
          <option value="high">High urgency</option>
        </select>
        <button type="submit" className="btn-primary w-full justify-center text-sm" data-testid="support-submit">
          Send to facilitator
        </button>
      </form>
    </div>
  );
}

export default function SupportTab({ workshop }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ subject: "", content: "", urgency: "normal" });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/support-requests?workshop_id=${workshop.id}`);
      setItems(data);
    } catch (err) {
      console.error("Support requests load failed:", err?.message || err);
    }
  }, [workshop.id]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/support-requests", { ...form, workshop_id: workshop.id });
      setForm({ subject: "", content: "", urgency: "normal" });
      load();
      toast.success("Your support request was sent.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="tab-support">
      <div className="lg:col-span-2 space-y-3">
        {items.length === 0 && <div className="card p-8 text-center text-sm text-[#5C6B6B]">No support requests yet.</div>}
        {items.map((s) => <SupportItem key={s.id} item={s} />)}
      </div>
      <NewSupportForm form={form} setForm={setForm} onSubmit={submit} />
    </div>
  );
}
