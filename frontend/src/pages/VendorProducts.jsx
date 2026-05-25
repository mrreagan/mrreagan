import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { ArrowLeft, Plus, Pencil, Trash2, ShoppingBag, Search, AlertTriangle, Eye, EyeOff, Bot } from "lucide-react";
import VendorPDMPanel from "../components/VendorPDMPanel";

const EMPTY = {
  name: "",
  description: "",
  price: "",
  image_url: "",
  category: "general",
};

const CATEGORY_OPTIONS = [
  "apparel", "journals", "books", "prints", "stickers", "decks",
  "home", "bags", "accessories", "digital", "general",
];

const STATUS_BADGE = {
  active:      { label: "Live",          cls: "bg-[#2E5C46]/10 text-[#2E5C46] border-[#2E5C46]/30", icon: Eye },
  flagged:     { label: "Flagged",       cls: "bg-[#C9A961]/15 text-[#8B7128] border-[#C9A961]/40", icon: AlertTriangle },
  unpublished: { label: "Unpublished",   cls: "bg-[#B86A5C]/10 text-[#B86A5C] border-[#B86A5C]/30", icon: EyeOff },
};

function StatusBadge({ status }) {
  const cfg = STATUS_BADGE[status] || STATUS_BADGE.active;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${cfg.cls}`} data-testid={`vendor-product-status-${status}`}>
      <Icon size={11} strokeWidth={1.5} /> {cfg.label}
    </span>
  );
}

function ProductDrawer({ open, initial, onClose, onSaved }) {
  const isEdit = Boolean(initial?.id);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(initial ? {
      name: initial.name || "",
      description: initial.description || "",
      price: initial.price ?? "",
      image_url: initial.image_url || "",
      category: initial.category || "general",
    } : EMPTY);
  }, [open, initial]);

  if (!open) return null;
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (form.name.trim().length < 2) return toast.error("Name must be at least 2 characters");
    if (form.description.trim().length < 10) return toast.error("Description must be at least 10 characters");
    const price = parseFloat(form.price);
    if (!Number.isFinite(price) || price < 0) return toast.error("Price must be a non-negative number");
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        price,
        image_url: form.image_url.trim(),
        category: form.category,
      };
      if (isEdit) {
        await api.put(`/vendor/products/${initial.id}`, payload);
        toast.success("Product updated");
      } else {
        await api.post("/vendor/products", payload);
        toast.success("Product live in the storefront");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not save");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="vendor-product-drawer">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="ml-auto h-full w-full max-w-lg bg-white shadow-xl overflow-y-auto relative">
        <div className="p-6 border-b border-[#E5E1D8] flex items-center justify-between">
          <h2 className="font-serif text-xl">{isEdit ? "Edit product" : "New product"}</h2>
          <button onClick={onClose} className="text-sm text-[#5C6B6B] hover:text-[#476B6B]">Close</button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-3">
          <label className="block">
            <span className="label">Name</span>
            <input className="input-field mt-1" value={form.name} onChange={(e) => update("name", e.target.value)} maxLength={200} required data-testid="vendor-product-name" />
          </label>
          <label className="block">
            <span className="label">Description</span>
            <textarea className="input-field mt-1 min-h-[140px]" value={form.description} onChange={(e) => update("description", e.target.value)} maxLength={4000} required data-testid="vendor-product-description" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="label">Price (USD)</span>
              <input className="input-field mt-1" type="number" step="0.01" min="0" value={form.price} onChange={(e) => update("price", e.target.value)} required data-testid="vendor-product-price" />
            </label>
            <label className="block">
              <span className="label">Category</span>
              <select className="input-field mt-1" value={form.category} onChange={(e) => update("category", e.target.value)} data-testid="vendor-product-category">
                {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="label">Image URL</span>
            <input className="input-field mt-1" placeholder="https://… or /api/static/products/your-image.png" value={form.image_url} onChange={(e) => update("image_url", e.target.value)} data-testid="vendor-product-image-url" />
          </label>
          {form.image_url && (
            <div className="w-full aspect-square max-w-[200px] bg-[#FAF8F5] rounded overflow-hidden border border-[#E5E1D8]">
              <img src={form.image_url} alt="preview" className="w-full h-full object-cover" onError={(e) => { e.target.style.display = "none"; }} />
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center" data-testid="vendor-product-submit">
              {saving ? "Saving…" : isEdit ? "Save changes" : "Publish product"}
            </button>
            <button type="button" onClick={onClose} className="btn-outline">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function VendorProducts() {
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [pdmOpen, setPdmOpen] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/partners/my-profiles"),
      api.get("/vendor/products"),
    ])
      .then(([profRes, prodRes]) => {
        const hasActiveVendor = (profRes.data || []).some(
          (p) => p.partner_type === "vendor" && p.status === "active",
        );
        if (!hasActiveVendor) {
          setAccessDenied(true);
        } else {
          setProducts(prodRes.data);
        }
      })
      .catch(() => setAccessDenied(true))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const visible = useMemo(() => {
    return products.filter((p) => {
      if (statusFilter !== "all" && p.moderation_status !== statusFilter) return false;
      if (search.trim()) {
        const s = search.toLowerCase();
        return p.name.toLowerCase().includes(s) || p.description.toLowerCase().includes(s) || (p.category || "").toLowerCase().includes(s);
      }
      return true;
    });
  }, [products, search, statusFilter]);

  const openNew = () => { setEditing(null); setDrawerOpen(true); };
  const openEdit = (p) => { setEditing(p); setDrawerOpen(true); };
  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/vendor/products/${p.id}`);
      toast.success("Product deleted");
      setProducts((prev) => prev.filter((x) => x.id !== p.id));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Delete failed");
    }
  };

  if (!user) return null;

  return (
    <div className="container-page py-12" data-testid="vendor-products-page">
      <Link to="/dashboard/partner" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to partner workspace
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="label">Vendor catalog</span>
          <h1 className="editorial-h1 mt-2">Your products</h1>
          <div className="divider-flame" />
          <p className="text-sm text-[#5C6B6B]">
            {accessDenied
              ? "You need an approved vendor partner profile to manage products."
              : `${products.length} product${products.length === 1 ? "" : "s"} in your catalog. Products go live the moment you publish — admins may flag or unpublish anytime.`}
          </p>
        </div>
        {!accessDenied && (
          <div className="flex gap-2">
            <button onClick={() => setPdmOpen(true)} className="btn-outline inline-flex items-center gap-2" data-testid="vendor-pdm-open">
              <Bot size={14} strokeWidth={1.5} /> Product AI
            </button>
            <button onClick={openNew} className="btn-primary" data-testid="vendor-product-new-button">
              <Plus size={16} strokeWidth={1.5} /> New product
            </button>
          </div>
        )}
      </div>
      <VendorPDMPanel open={pdmOpen} onClose={() => setPdmOpen(false)} onPickResult={(r) => {
        if (typeof r === "string") {
          if (r.startsWith("/api/") || r.startsWith("http")) {
            setForm((f) => ({ ...f, image_url: r }));
          } else if (r.length > 60) {
            setForm((f) => ({ ...f, description: r }));
          }
        }
        setPdmOpen(false);
        setDrawerOpen(true);
      }} />

      {accessDenied ? (
        <div className="card p-10 mt-10 text-center" data-testid="vendor-access-denied">
          <ShoppingBag size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
          <p className="font-serif text-xl mt-3">No active vendor profile yet</p>
          <p className="text-sm text-[#5C6B6B] mt-2">Apply to become a vendor partner. Once approved you'll be able to publish products here.</p>
          <Link to="/partners/apply" className="btn-primary mt-6 inline-block">Apply now</Link>
        </div>
      ) : (
        <>
          <div className="mt-8 flex flex-wrap items-center gap-3" data-testid="vendor-products-toolbar">
            <div className="relative flex-1 min-w-[240px]">
              <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search your catalog…"
                className="input-field pl-9"
                data-testid="vendor-products-search"
              />
            </div>
            <div className="flex gap-1 flex-wrap" data-testid="vendor-products-status-filter">
              {[
                { id: "all", label: "All" },
                { id: "active", label: "Live" },
                { id: "flagged", label: "Flagged" },
                { id: "unpublished", label: "Unpublished" },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id)}
                  className={`px-3 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
                    statusFilter === f.id ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
                  }`}
                  data-testid={`vendor-status-filter-${f.id}`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="card mt-6 overflow-x-auto" data-testid="vendor-products-table">
            {loading ? (
              <div className="p-12 text-center text-sm text-[#5C6B6B]">Loading your catalog…</div>
            ) : visible.length === 0 ? (
              <div className="p-12 text-center">
                <ShoppingBag size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
                <p className="font-serif text-lg mt-3">Nothing here yet.</p>
                <p className="text-sm text-[#5C6B6B] mt-1">
                  {search || statusFilter !== "all" ? "No products match your filters." : "Publish your first product to start selling through Birthright."}
                </p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-[#FAF8F5] border-b border-[#E5E1D8]">
                  <tr>
                    <th className="p-3 text-left label w-20">Image</th>
                    <th className="p-3 text-left label">Product</th>
                    <th className="p-3 text-left label">Category</th>
                    <th className="p-3 text-left label">Price</th>
                    <th className="p-3 text-left label">Status</th>
                    <th className="p-3 text-right label">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((p) => (
                    <tr key={p.id} className="border-b border-[#E5E1D8] last:border-0" data-testid={`vendor-product-row-${p.id}`}>
                      <td className="p-3">
                        <div className="w-14 h-14 bg-[#E5E1D8] rounded overflow-hidden">
                          {p.image_url ? <img src={p.image_url} alt="" className="w-full h-full object-cover" /> : null}
                        </div>
                      </td>
                      <td className="p-3">
                        <p className="font-medium text-sm">{p.name}</p>
                        <p className="text-xs text-[#5C6B6B] line-clamp-1 max-w-md">{p.description}</p>
                        {p.moderation_note && p.moderation_status !== "active" && (
                          <p className="text-[11px] italic text-[#B86A5C] mt-1">Admin note: {p.moderation_note}</p>
                        )}
                      </td>
                      <td className="p-3 text-xs text-[#5C6B6B] uppercase tracking-wider">{p.category}</td>
                      <td className="p-3 text-sm">${Number(p.price).toFixed(2)}</td>
                      <td className="p-3"><StatusBadge status={p.moderation_status} /></td>
                      <td className="p-3">
                        <div className="flex items-center gap-2 justify-end">
                          <Link to={`/shop/${p.id}`} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]" title="View public page" data-testid={`vendor-product-view-${p.id}`}>
                            <Eye size={14} strokeWidth={1.5} />
                          </Link>
                          <button onClick={() => openEdit(p)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]" title="Edit" data-testid={`vendor-product-edit-${p.id}`}>
                            <Pencil size={14} strokeWidth={1.5} />
                          </button>
                          <button onClick={() => remove(p)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#B86A5C]" title="Delete" data-testid={`vendor-product-delete-${p.id}`}>
                            <Trash2 size={14} strokeWidth={1.5} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      <ProductDrawer open={drawerOpen} initial={editing} onClose={() => setDrawerOpen(false)} onSaved={load} />
    </div>
  );
}
