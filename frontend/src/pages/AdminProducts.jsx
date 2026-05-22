import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { ArrowLeft, Plus, Pencil, Trash2, Lock, ShoppingBag, Search } from "lucide-react";

const EMPTY = {
  name: "",
  description: "",
  price: "",
  type: "merch",
  workshop_id: "",
  image_url: "",
  inventory: 50,
  category: "general",
};

const CATEGORY_OPTIONS = [
  "apparel", "journals", "books", "prints", "stickers", "decks",
  "home", "bags", "accessories", "digital", "general",
];

function ProductRow({ product, onEdit, onDelete }) {
  const isMaterial = product.type === "workshop_material";
  return (
    <tr className="border-b border-[#E5E1D8] last:border-0" data-testid={`admin-product-row-${product.id}`}>
      <td className="p-3">
        <div className="w-14 h-14 bg-[#E5E1D8] rounded overflow-hidden">
          {product.image_url ? (
            <img src={product.image_url} alt="" className="w-full h-full object-cover" />
          ) : null}
        </div>
      </td>
      <td className="p-3">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{product.name}</span>
          {isMaterial && <Lock size={12} strokeWidth={1.5} className="text-[#C9A961]" />}
        </div>
        <p className="text-xs text-[#5C6B6B] line-clamp-1 max-w-md">{product.description}</p>
      </td>
      <td className="p-3 text-xs text-[#5C6B6B] uppercase tracking-wider">{product.category}</td>
      <td className="p-3 text-sm">${Number(product.price).toFixed(2)}</td>
      <td className="p-3 text-xs text-[#5C6B6B]">{product.inventory}</td>
      <td className="p-3">
        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={() => onEdit(product)}
            className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]"
            title="Edit"
            data-testid={`admin-product-edit-${product.id}`}
          >
            <Pencil size={14} strokeWidth={1.5} />
          </button>
          <button
            onClick={() => onDelete(product)}
            className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#B86A5C]"
            title="Delete"
            data-testid={`admin-product-delete-${product.id}`}
          >
            <Trash2 size={14} strokeWidth={1.5} />
          </button>
        </div>
      </td>
    </tr>
  );
}

function ProductFormDrawer({ open, initial, workshops, onClose, onSaved }) {
  const isEdit = Boolean(initial?.id);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({
        ...EMPTY,
        ...(initial || {}),
        price: initial?.price ?? "",
        workshop_id: initial?.workshop_id ?? "",
      });
    }
  }, [open, initial]);

  if (!open) return null;

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.description.trim() || !form.price) {
      toast.error("Name, description, and price are required");
      return;
    }
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      price: parseFloat(form.price),
      type: form.type,
      workshop_id: form.type === "workshop_material" ? form.workshop_id || null : null,
      image_url: form.image_url.trim(),
      inventory: parseInt(form.inventory, 10) || 0,
      category: form.category || "general",
    };
    setSaving(true);
    try {
      if (isEdit) {
        // PUT only accepts ProductUpdate fields (no type / workshop_id)
        const updateBody = {
          name: payload.name,
          description: payload.description,
          price: payload.price,
          image_url: payload.image_url,
          inventory: payload.inventory,
          category: payload.category,
        };
        await api.put(`/products/${initial.id}`, updateBody);
        toast.success("Product updated");
      } else {
        await api.post("/products", payload);
        toast.success("Product created");
      }
      onSaved();
      onClose();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Save failed";
      toast.error(typeof msg === "string" ? msg : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/30" data-testid="admin-product-drawer">
      <button aria-label="close" className="flex-1" onClick={onClose} />
      <form
        onSubmit={submit}
        className="w-full max-w-lg bg-white shadow-2xl overflow-y-auto p-8 flex flex-col gap-4"
      >
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-2xl">{isEdit ? "Edit product" : "New product"}</h2>
          <button type="button" onClick={onClose} className="text-sm text-[#5C6B6B] hover:text-[#1A2424]">
            Close
          </button>
        </div>
        <div className="divider-flame" />

        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          Name
          <input
            className="input-field mt-1"
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            data-testid="admin-product-form-name"
            required
          />
        </label>

        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          Description
          <textarea
            className="input-field mt-1 min-h-[100px]"
            value={form.description}
            onChange={(e) => update("description", e.target.value)}
            data-testid="admin-product-form-description"
            required
          />
        </label>

        <div className="grid grid-cols-2 gap-4">
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Price (USD)
            <input
              type="number" step="0.01" min="0"
              className="input-field mt-1"
              value={form.price}
              onChange={(e) => update("price", e.target.value)}
              data-testid="admin-product-form-price"
              required
            />
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Inventory
            <input
              type="number" min="0"
              className="input-field mt-1"
              value={form.inventory}
              onChange={(e) => update("inventory", e.target.value)}
              data-testid="admin-product-form-inventory"
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Type
            <select
              className="input-field mt-1"
              value={form.type}
              onChange={(e) => update("type", e.target.value)}
              disabled={isEdit}
              data-testid="admin-product-form-type"
            >
              <option value="merch">Public merch</option>
              <option value="workshop_material">Workshop material</option>
            </select>
          </label>
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Category
            <select
              className="input-field mt-1"
              value={form.category}
              onChange={(e) => update("category", e.target.value)}
              data-testid="admin-product-form-category"
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>

        {form.type === "workshop_material" && (
          <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
            Linked workshop
            <select
              className="input-field mt-1"
              value={form.workshop_id || ""}
              onChange={(e) => update("workshop_id", e.target.value)}
              disabled={isEdit}
              data-testid="admin-product-form-workshop"
            >
              <option value="">— Select workshop —</option>
              {workshops.map((w) => (
                <option key={w.id} value={w.id}>{w.title}</option>
              ))}
            </select>
            {isEdit && (
              <p className="text-[10px] mt-1 text-[#5C6B6B] normal-case tracking-normal">
                Type and linked workshop cannot be changed after creation. Delete and recreate to change.
              </p>
            )}
          </label>
        )}

        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          Image URL
          <input
            className="input-field mt-1"
            value={form.image_url}
            onChange={(e) => update("image_url", e.target.value)}
            placeholder="https://...  or  /api/static/products/your-image.png"
            data-testid="admin-product-form-image"
          />
        </label>
        {form.image_url && (
          <div className="w-full aspect-square max-w-[200px] bg-[#FAF8F5] rounded overflow-hidden border border-[#E5E1D8]">
            <img src={form.image_url} alt="preview" className="w-full h-full object-cover" />
          </div>
        )}

        <div className="flex gap-3 mt-4">
          <button
            type="submit"
            disabled={saving}
            className="btn-primary flex-1 justify-center"
            data-testid="admin-product-form-submit"
          >
            {saving ? "Saving..." : isEdit ? "Save changes" : "Create product"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="btn-outline"
            data-testid="admin-product-form-cancel"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

export default function AdminProducts() {
  const [products, setProducts] = useState([]);
  const [workshops, setWorkshops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/products"),
      api.get("/workshops"),
    ])
      .then(([pRes, wRes]) => {
        setProducts(pRes.data);
        setWorkshops(wRes.data);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const visible = useMemo(() => {
    return products.filter((p) => {
      if (filter !== "all" && p.type !== filter) return false;
      if (search.trim()) {
        const s = search.toLowerCase();
        return (
          p.name?.toLowerCase().includes(s) ||
          p.description?.toLowerCase().includes(s) ||
          p.category?.toLowerCase().includes(s)
        );
      }
      return true;
    });
  }, [products, filter, search]);

  const openNew = () => { setEditing(null); setDrawerOpen(true); };
  const openEdit = (p) => { setEditing(p); setDrawerOpen(true); };

  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/products/${p.id}`);
      toast.success("Product deleted");
      setProducts((prev) => prev.filter((x) => x.id !== p.id));
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-products-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to admin
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="label">Catalog</span>
          <h1 className="editorial-h1 mt-2">Manage products</h1>
          <div className="divider-flame" />
          <p className="text-sm text-[#5C6B6B]">
            {products.length} item{products.length === 1 ? "" : "s"} in the storefront.
          </p>
        </div>
        <button
          onClick={openNew}
          className="btn-primary"
          data-testid="admin-product-new-button"
        >
          <Plus size={16} strokeWidth={1.5} /> New product
        </button>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-3" data-testid="admin-products-toolbar">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, description, category..."
            className="input-field pl-9"
            data-testid="admin-products-search"
          />
        </div>
        <div className="flex gap-1">
          {[
            { id: "all", label: "All" },
            { id: "merch", label: "Public merch" },
            { id: "workshop_material", label: "Workshop materials" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-3 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
                filter === f.id
                  ? "bg-[#476B6B] text-white border-[#476B6B]"
                  : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`admin-products-filter-${f.id}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card mt-6 overflow-x-auto" data-testid="admin-products-table">
        {loading ? (
          <div className="p-12 text-center text-sm text-[#5C6B6B]">Loading catalog...</div>
        ) : visible.length === 0 ? (
          <div className="p-12 text-center">
            <ShoppingBag size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
            <p className="font-serif text-lg mt-3">Nothing here yet.</p>
            <p className="text-sm text-[#5C6B6B] mt-1">
              {search || filter !== "all"
                ? "No products match your filters."
                : "Create your first product to populate the storefront."}
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
                <th className="p-3 text-left label">Stock</th>
                <th className="p-3 text-right label">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((p) => (
                <ProductRow key={p.id} product={p} onEdit={openEdit} onDelete={remove} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <ProductFormDrawer
        open={drawerOpen}
        initial={editing}
        workshops={workshops}
        onClose={() => setDrawerOpen(false)}
        onSaved={load}
      />
    </div>
  );
}
