import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Pencil, Trash2, Plus, X } from "lucide-react";

const EMPTY = {
  slug: "",
  title: "",
  headline: "",
  who_you_are: "",
  what_youll_do: "",
  what_you_bring: "",
  time_commitment: "",
  compensation_summary: "Equity in mission — birthright is a not-for-profit and does not currently provide monetary compensation.",
  order: 0,
  open: true,
};

export default function AdminFoundationRoles() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null | "new" | role.slug
  const [form, setForm] = useState(EMPTY);

  const load = () => {
    setLoading(true);
    api.get("/admin/foundation-roles")
      .then((r) => setRoles(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const startEdit = (role) => {
    setForm({ ...role });
    setEditing(role.slug);
  };
  const startNew = () => {
    setForm(EMPTY);
    setEditing("new");
  };
  const cancel = () => { setEditing(null); setForm(EMPTY); };

  const save = async () => {
    try {
      if (editing === "new") {
        await api.post("/admin/foundation-roles", form);
        toast.success("Role created.");
      } else {
        await api.put(`/admin/foundation-roles/${editing}`, form);
        toast.success("Role updated.");
      }
      cancel();
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed.");
    }
  };

  const del = async (slug) => {
    if (!window.confirm(`Delete role "${slug}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/admin/foundation-roles/${slug}`);
      toast.success("Role deleted.");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Delete failed.");
    }
  };

  const toggleOpen = async (role) => {
    try {
      await api.put(`/admin/foundation-roles/${role.slug}`, { open: !role.open });
      load();
    } catch (e) {
      toast.error("Update failed.");
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-foundation-roles-page">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <span className="label">Admin</span>
          <h1 className="editorial-h1 mt-2">Foundation roles</h1>
          <p className="text-sm text-[#5C6B6B] mt-2 max-w-xl">
            Open seats on the governing board, advertised at <code>/join-us</code>.
            Applications appear in the <a href="/admin/foundation-applications" className="underline text-[#476B6B]">applications queue</a>.
          </p>
        </div>
        <button onClick={startNew} className="btn-primary inline-flex items-center gap-2" data-testid="new-role-btn">
          <Plus size={14} strokeWidth={1.5} /> New role
        </button>
      </div>
      <div className="divider-flame" />

      {loading ? (
        <p className="text-sm text-[#5C6B6B]">Loading...</p>
      ) : (
        <div className="space-y-3 mt-4">
          {roles.map((r) => (
            <div key={r.slug} className="card p-5 flex items-start gap-4" data-testid={`admin-role-${r.slug}`}>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-serif text-xl">{r.title}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider ${r.open ? "bg-[#2E5C46] text-white" : "bg-[#E5E1D8] text-[#5C6B6B]"}`}>
                    {r.open ? "Open" : "Closed"}
                  </span>
                </div>
                <p className="text-xs text-[#5C6B6B] mt-1 font-mono">{r.slug} · order {r.order} · {r.time_commitment}</p>
                <p className="text-sm text-[#1A2424] mt-2">{r.headline}</p>
              </div>
              <div className="flex flex-col gap-2 items-end">
                <button onClick={() => toggleOpen(r)} className="text-xs underline text-[#476B6B]" data-testid={`toggle-open-${r.slug}`}>
                  {r.open ? "Close" : "Reopen"}
                </button>
                <button onClick={() => startEdit(r)} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`edit-${r.slug}`}>
                  <Pencil size={12} strokeWidth={1.5} /> Edit
                </button>
                <button onClick={() => del(r.slug)} className="text-xs text-[#9E3C3C] inline-flex items-center gap-1" data-testid={`del-${r.slug}`}>
                  <Trash2 size={12} strokeWidth={1.5} /> Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {editing !== null && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={cancel}>
          <div className="bg-white max-w-2xl w-full rounded-xl p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="role-edit-modal">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-serif text-2xl">{editing === "new" ? "New role" : "Edit role"}</h2>
              <button onClick={cancel}><X size={20} strokeWidth={1.5} /></button>
            </div>
            <div className="space-y-4">
              {editing === "new" && (
                <Field label="Slug (url segment)" v={form.slug} onChange={(v) => setForm({ ...form, slug: v })} testid="form-slug" />
              )}
              <Field label="Title" v={form.title} onChange={(v) => setForm({ ...form, title: v })} testid="form-title" />
              <Field label="Headline" v={form.headline} onChange={(v) => setForm({ ...form, headline: v })} testid="form-headline" />
              <Textarea label="Who you are" v={form.who_you_are} onChange={(v) => setForm({ ...form, who_you_are: v })} testid="form-who" />
              <Textarea label="What you'll do" v={form.what_youll_do} onChange={(v) => setForm({ ...form, what_youll_do: v })} testid="form-do" />
              <Textarea label="What you bring" v={form.what_you_bring} onChange={(v) => setForm({ ...form, what_you_bring: v })} testid="form-bring" />
              <Field label="Time commitment" v={form.time_commitment} onChange={(v) => setForm({ ...form, time_commitment: v })} testid="form-time" />
              <Textarea label="Compensation summary" v={form.compensation_summary} onChange={(v) => setForm({ ...form, compensation_summary: v })} testid="form-comp" />
              <div className="flex gap-3">
                <Field label="Order" v={form.order} onChange={(v) => setForm({ ...form, order: parseInt(v) || 0 })} testid="form-order" />
                <label className="flex items-center gap-2 text-sm mt-6">
                  <input type="checkbox" checked={form.open} onChange={(e) => setForm({ ...form, open: e.target.checked })} data-testid="form-open" />
                  Open for applications
                </label>
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={save} className="btn-primary flex-1" data-testid="form-save">Save</button>
                <button onClick={cancel} className="btn-outline">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, v, onChange, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <input value={v} onChange={(e) => onChange(e.target.value)} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
function Textarea({ label, v, onChange, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <textarea value={v} onChange={(e) => onChange(e.target.value)} rows={4} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
