import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";

const EMPTY = {
  title: "",
  slug: "",
  short_description: "",
  full_description: "",
  facilitator_id: "",
  location_name: "Birthright Community Hall",
  location_address: "2148 W Earll Dr, Phoenix, AZ 85015",
  map_url: "https://maps.google.com/?q=2148+W+Earll+Dr+Phoenix+AZ+85015",
  directions_notes: "",
  start_date: "",
  end_date: "",
  capacity: 24,
  early_bird_price: "",
  regular_price: "",
  early_bird_until: "",
  image_url: "",
  materials_included: "",
  status: "upcoming",
};

function toIso(local) {
  if (!local) return "";
  // datetime-local format: 2026-06-12T18:30
  return new Date(local).toISOString();
}
function fromIso(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return "";
  }
}

function buildWorkshopPayload(form, initial, currentUser, isFacilitator) {
  return {
    title: form.title.trim(),
    slug: form.slug.trim().toLowerCase().replace(/[^a-z0-9-]+/g, "-"),
    short_description: form.short_description.trim(),
    full_description: form.full_description.trim(),
    facilitator_id: isFacilitator ? currentUser.id : form.facilitator_id,
    location_name: form.location_name,
    location_address: form.location_address,
    map_url: form.map_url,
    directions_notes: form.directions_notes,
    start_date: toIso(form.start_date),
    end_date: toIso(form.end_date),
    capacity: parseInt(form.capacity, 10) || 1,
    early_bird_price: parseFloat(form.early_bird_price) || 0,
    regular_price: parseFloat(form.regular_price) || 0,
    early_bird_until: form.early_bird_until ? toIso(form.early_bird_until) : null,
    image_url: form.image_url,
    materials_included: form.materials_included
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
    faq: initial?.faq || [],
    status: form.status,
  };
}

function validateWorkshopPayload(form, payload, isEdit) {
  if (!form.title.trim() || !form.slug.trim() || !form.short_description.trim()) {
    return "Title, slug, and short description are required";
  }
  if (!isEdit && !payload.facilitator_id) return "Please select a facilitator";
  if (!payload.start_date || !payload.end_date) return "Start and end dates are required";
  return null;
}

async function persistWorkshop(payload, initial, isEdit) {
  if (isEdit) {
    const updateBody = { ...payload };
    delete updateBody.slug;          // slug immutable after creation
    delete updateBody.facilitator_id;
    await api.put(`/workshops/${initial.id}`, updateBody);
    return "Workshop updated";
  }
  await api.post("/workshops", payload);
  return "Workshop created";
}

export default function WorkshopFormDrawer({ open, initial, facilitators, currentUser, onClose, onSaved }) {
  const isEdit = Boolean(initial?.id);
  const isFacilitator = currentUser?.role === "facilitator";
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        ...EMPTY,
        ...initial,
        start_date: fromIso(initial.start_date),
        end_date: fromIso(initial.end_date),
        early_bird_until: fromIso(initial.early_bird_until),
        materials_included: (initial.materials_included || []).join("\n"),
        early_bird_price: initial.early_bird_price ?? "",
        regular_price: initial.regular_price ?? "",
      });
    } else {
      setForm({
        ...EMPTY,
        facilitator_id: isFacilitator ? currentUser.id : "",
      });
    }
  }, [open, initial, isFacilitator, currentUser]);

  if (!open) return null;
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    const payload = buildWorkshopPayload(form, initial, currentUser, isFacilitator);
    const error = validateWorkshopPayload(form, payload, isEdit);
    if (error) { toast.error(error); return; }
    setSaving(true);
    try {
      const message = await persistWorkshop(payload, initial, isEdit);
      toast.success(message);
      onSaved();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/30" data-testid="admin-workshop-drawer">
      <button aria-label="close" className="flex-1" onClick={onClose} />
      <form onSubmit={submit} className="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto p-8 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-2xl">{isEdit ? "Edit workshop" : "New workshop"}</h2>
          <button type="button" onClick={onClose} className="text-sm text-[#5C6B6B] hover:text-[#1A2424]">Close</button>
        </div>
        <div className="divider-flame" />

        <div className="grid grid-cols-2 gap-4">
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Title
            <input className="input-field mt-1" value={form.title} onChange={(e) => update("title", e.target.value)} data-testid="ws-form-title" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Slug (URL path)
            <input className="input-field mt-1" value={form.slug} onChange={(e) => update("slug", e.target.value)} disabled={isEdit} placeholder="e.g. foundations-fall-2026" data-testid="ws-form-slug" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Short description
            <input className="input-field mt-1" value={form.short_description} onChange={(e) => update("short_description", e.target.value)} data-testid="ws-form-short" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Full description
            <textarea className="input-field mt-1 min-h-[120px]" value={form.full_description} onChange={(e) => update("full_description", e.target.value)} data-testid="ws-form-full" />
          </label>

          {!isFacilitator && !isEdit && (
            <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
              Facilitator
              <select className="input-field mt-1" value={form.facilitator_id} onChange={(e) => update("facilitator_id", e.target.value)} required data-testid="ws-form-facilitator">
                <option value="">— Select facilitator —</option>
                {facilitators.map((f) => (
                  <option key={f.id} value={f.id}>{f.first_name} {f.last_name}</option>
                ))}
              </select>
            </label>
          )}

          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Start (local time)
            <input type="datetime-local" className="input-field mt-1" value={form.start_date} onChange={(e) => update("start_date", e.target.value)} required data-testid="ws-form-start" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            End (local time)
            <input type="datetime-local" className="input-field mt-1" value={form.end_date} onChange={(e) => update("end_date", e.target.value)} required data-testid="ws-form-end" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Early-bird cutoff (optional)
            <input type="datetime-local" className="input-field mt-1" value={form.early_bird_until} onChange={(e) => update("early_bird_until", e.target.value)} data-testid="ws-form-eb-until" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Capacity
            <input type="number" min="1" className="input-field mt-1" value={form.capacity} onChange={(e) => update("capacity", e.target.value)} required data-testid="ws-form-capacity" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Early-bird price ($)
            <input type="number" step="0.01" min="0" className="input-field mt-1" value={form.early_bird_price} onChange={(e) => update("early_bird_price", e.target.value)} required data-testid="ws-form-eb-price" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Regular price ($)
            <input type="number" step="0.01" min="0" className="input-field mt-1" value={form.regular_price} onChange={(e) => update("regular_price", e.target.value)} required data-testid="ws-form-reg-price" />
          </label>

          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Location name
            <input className="input-field mt-1" value={form.location_name} onChange={(e) => update("location_name", e.target.value)} data-testid="ws-form-loc-name" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Location address
            <input className="input-field mt-1" value={form.location_address} onChange={(e) => update("location_address", e.target.value)} data-testid="ws-form-loc-addr" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Google map URL (optional)
            <input className="input-field mt-1" value={form.map_url} onChange={(e) => update("map_url", e.target.value)} data-testid="ws-form-map" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Directions / parking notes
            <textarea className="input-field mt-1 min-h-[60px]" value={form.directions_notes} onChange={(e) => update("directions_notes", e.target.value)} data-testid="ws-form-directions" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Materials included (one per line)
            <textarea className="input-field mt-1 min-h-[80px]" value={form.materials_included} onChange={(e) => update("materials_included", e.target.value)} placeholder={"Workbook\nTwo days of facilitated practice\nLight meals"} data-testid="ws-form-materials" />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Cover image URL
            <input className="input-field mt-1" value={form.image_url} onChange={(e) => update("image_url", e.target.value)} data-testid="ws-form-image" />
          </label>
          {form.image_url && (
            <div className="col-span-2 w-full max-w-md aspect-[16/9] bg-[#FAF8F5] rounded overflow-hidden border border-[#E5E1D8]">
              <img src={form.image_url} alt="preview" className="w-full h-full object-cover" />
            </div>
          )}
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B] col-span-2">
            Status
            <select className="input-field mt-1" value={form.status} onChange={(e) => update("status", e.target.value)} data-testid="ws-form-status">
              <option value="draft">Draft (hidden)</option>
              <option value="upcoming">Upcoming</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
            </select>
          </label>
        </div>

        {isEdit && initial?.check_in_code && (
          <div className="bg-[#FAF8F5] border border-[#E5E1D8] p-3 rounded">
            <p className="text-[11px] uppercase tracking-wider text-[#5C6B6B]">Check-in code (auto-generated, read-only)</p>
            <p className="font-serif text-xl tracking-widest mt-1">{initial.check_in_code}</p>
          </div>
        )}

        <div className="flex gap-3 mt-4">
          <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center" data-testid="ws-form-submit">
            {saving ? "Saving..." : isEdit ? "Save changes" : "Create workshop"}
          </button>
          <button type="button" onClick={onClose} className="btn-outline" data-testid="ws-form-cancel">Cancel</button>
        </div>
      </form>
    </div>
  );
}
