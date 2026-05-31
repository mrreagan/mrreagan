import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Plus, MapPin } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export default function GatherPropose() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const parentSlug = params.get("under") || "";
  const [parent, setParent] = useState(null);
  const [f, setF] = useState({ label: "", kind: "city", lat: "", lng: "", note: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) { navigate("/sign-in"); return; }
    if (!parentSlug) return;
    api.get(`/gather/community/${parentSlug}`).then((r) => {
      setParent(r.data.community);
      // Default kind based on parent kind
      if (r.data.community.kind === "city") setF((p) => ({ ...p, kind: "neighborhood" }));
    });
  }, [parentSlug, user, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    if (!parentSlug) return toast.error("No parent community selected");
    setBusy(true);
    try {
      await api.post("/gather/propose", {
        label: f.label.trim(),
        parent_slug: parentSlug,
        kind: f.kind,
        lat: f.lat ? parseFloat(f.lat) : undefined,
        lng: f.lng ? parseFloat(f.lng) : undefined,
        note: f.note,
      });
      toast.success("Proposal sent — admins will review");
      navigate(`/gather?under=${encodeURIComponent(parentSlug)}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Proposal failed");
    } finally { setBusy(false); }
  };

  if (!parentSlug) return (
    <div className="container-page py-12">
      <p className="text-sm">No parent community selected. <Link to="/gather" className="underline">Browse Gather →</Link></p>
    </div>
  );

  return (
    <div className="container-page py-12 max-w-xl" data-testid="gather-propose-page">
      <Link to={`/gather?under=${encodeURIComponent(parentSlug)}`} className="text-xs text-[#476B6B] hover:underline">← back</Link>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3"><Plus size={24} strokeWidth={1.2} /> Propose a community</h1>
      <div className="divider-flame" />
      {parent && (
        <p className="text-sm text-[#5C6B6B]">
          Under: <span className="font-medium text-[#0F2424]">{parent.label}</span> ({parent.kind})
        </p>
      )}

      <form onSubmit={submit} className="card p-4 mt-6 space-y-3 text-sm" data-testid="gather-propose-form">
        <label className="block">
          <span className="block label !mt-0 !mb-1">Name (e.g. Santa Cruz)</span>
          <input value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} required minLength={2} className="input-field w-full" data-testid="gather-propose-label" />
        </label>
        <label className="block">
          <span className="block label !mt-0 !mb-1">Kind</span>
          <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className="input-field w-full" data-testid="gather-propose-kind">
            <option value="city">City</option>
            <option value="neighborhood">Neighborhood</option>
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="block label !mt-0 !mb-1">Latitude (optional)</span>
            <input value={f.lat} onChange={(e) => setF({ ...f, lat: e.target.value })} type="number" step="0.0001" className="input-field w-full" data-testid="gather-propose-lat" />
          </label>
          <label className="block">
            <span className="block label !mt-0 !mb-1">Longitude (optional)</span>
            <input value={f.lng} onChange={(e) => setF({ ...f, lng: e.target.value })} type="number" step="0.0001" className="input-field w-full" data-testid="gather-propose-lng" />
          </label>
        </div>
        <label className="block">
          <span className="block label !mt-0 !mb-1">Note (why does this community need a Gather space?)</span>
          <textarea value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} className="input-field w-full" rows={3} data-testid="gather-propose-note" />
        </label>
        <button disabled={busy} className="btn-primary text-sm inline-flex items-center gap-1" data-testid="gather-propose-submit">
          <MapPin size={14} /> {busy ? "Sending…" : "Send proposal"}
        </button>
      </form>
    </div>
  );
}
