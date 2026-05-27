import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "../lib/api";
import { ArrowLeft, AlertTriangle, EyeOff, Eye, Flag, Undo2, Search } from "lucide-react";

const TABS = [
  { id: "all", label: "All vendor products" },
  { id: "active", label: "Live" },
  { id: "flagged", label: "Flagged" },
  { id: "unpublished", label: "Unpublished" },
];

const STATUS_STYLE = {
  active:      "bg-[#2E5C46]/10 text-[#2E5C46] border-[#2E5C46]/30",
  flagged:     "bg-[#C9A961]/15 text-[#8B7128] border-[#C9A961]/40",
  unpublished: "bg-[#B86A5C]/10 text-[#B86A5C] border-[#B86A5C]/30",
};

export default function AdminVendorProducts() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("all");

  const load = () => {
    setLoading(true);
    const params = tab === "all" ? "" : `?status=${tab}`;
    api.get(`/admin/vendor-products${params}`)
      .then((r) => setProducts(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, [tab]);

  const visible = useMemo(() => {
    if (!search.trim()) return products;
    const s = search.toLowerCase();
    return products.filter((p) =>
      p.name.toLowerCase().includes(s) ||
      (p.vendor_name || "").toLowerCase().includes(s) ||
      (p.description || "").toLowerCase().includes(s)
    );
  }, [products, search]);

  const moderate = async (p, action, note = "") => {
    try {
      await api.post(`/admin/vendor-products/${p.id}/${action}`, { moderation_note: note });
      toast.success(`Product ${action}`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Action failed");
    }
  };

  const flag = async (p) => {
    const note = window.prompt("Why are you flagging this product? (visible to the vendor)") || "";
    if (!note.trim()) return;
    await moderate(p, "flag", note.trim());
  };
  const unpublish = async (p) => {
    const note = window.prompt("Reason for unpublishing? (visible to the vendor)") || "";
    if (!note.trim() && !window.confirm("Unpublish without a reason?")) return;
    await moderate(p, "unpublish", note.trim());
  };

  return (
    <div className="container-page py-12" data-testid="admin-vendor-products-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to admin
      </Link>

      <span className="label">Admin · Vendor catalog moderation</span>
      <h1 className="editorial-h1 mt-2">Vendor products</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B]">
        Vendors publish autonomously. Flag products that need attention or unpublish anything off-brand.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-3" data-testid="admin-vendor-toolbar">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by product, vendor name, description…"
            className="input-field pl-9"
            data-testid="admin-vendor-search"
          />
        </div>
        <div className="flex gap-1 flex-wrap">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
                tab === t.id ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`admin-vendor-tab-${t.id}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card mt-6 overflow-x-auto" data-testid="admin-vendor-table">
        {loading ? (
          <div className="p-12 text-center text-sm text-[#5C6B6B]">Loading…</div>
        ) : visible.length === 0 ? (
          <div className="p-12 text-center text-sm text-[#5C6B6B]">No vendor products match this view.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[#FAF8F5] border-b border-[#E5E1D8]">
              <tr>
                <th className="p-3 text-left label w-20">Image</th>
                <th className="p-3 text-left label">Product</th>
                <th className="p-3 text-left label">Vendor</th>
                <th className="p-3 text-left label">Price</th>
                <th className="p-3 text-left label">Status</th>
                <th className="p-3 text-right label">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((p) => (
                <tr key={p.id} className="border-b border-[#E5E1D8] last:border-0" data-testid={`admin-vendor-row-${p.id}`}>
                  <td className="p-3">
                    <div className="w-14 h-14 bg-[#E5E1D8] rounded overflow-hidden">
                      {p.image_url ? <img src={p.image_url} alt="" className="w-full h-full object-cover" /> : null}
                    </div>
                  </td>
                  <td className="p-3">
                    <p className="font-medium text-sm">{p.name}</p>
                    <p className="text-xs text-[#5C6B6B] line-clamp-1 max-w-md">{p.description}</p>
                    {p.moderation_note && (
                      <p className="text-[11px] italic text-[#B86A5C] mt-1">Note: {p.moderation_note}</p>
                    )}
                  </td>
                  <td className="p-3 text-xs">
                    {p.vendor_slug ? (
                      <Link to={`/partner/${p.vendor_slug}`} className="text-[#476B6B] hover:underline" data-testid={`admin-vendor-link-${p.id}`}>
                        {p.vendor_name || "(unnamed)"}
                      </Link>
                    ) : (
                      <span className="text-[#5C6B6B]">{p.vendor_name || "(unnamed)"}</span>
                    )}
                  </td>
                  <td className="p-3 text-sm">${Number(p.price).toFixed(2)}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${STATUS_STYLE[p.moderation_status] || ""}`} data-testid={`admin-vendor-status-${p.id}`}>
                      {p.moderation_status === "active" && <Eye size={11} strokeWidth={1.5} />}
                      {p.moderation_status === "flagged" && <AlertTriangle size={11} strokeWidth={1.5} />}
                      {p.moderation_status === "unpublished" && <EyeOff size={11} strokeWidth={1.5} />}
                      {p.moderation_status}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2 justify-end flex-wrap">
                      <Link to={`/equip/${p.id}`} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]" title="View product" data-testid={`admin-vendor-view-${p.id}`}>
                        <Eye size={14} strokeWidth={1.5} />
                      </Link>
                      {p.moderation_status === "active" && (
                        <button onClick={() => flag(p)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#C9A961]" title="Flag" data-testid={`admin-vendor-flag-${p.id}`}>
                          <Flag size={14} strokeWidth={1.5} />
                        </button>
                      )}
                      {p.moderation_status === "flagged" && (
                        <button onClick={() => moderate(p, "unflag")} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#2E5C46]" title="Clear flag" data-testid={`admin-vendor-unflag-${p.id}`}>
                          <Undo2 size={14} strokeWidth={1.5} />
                        </button>
                      )}
                      {p.moderation_status !== "unpublished" ? (
                        <button onClick={() => unpublish(p)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#B86A5C]" title="Unpublish" data-testid={`admin-vendor-unpublish-${p.id}`}>
                          <EyeOff size={14} strokeWidth={1.5} />
                        </button>
                      ) : (
                        <button onClick={() => moderate(p, "restore")} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#2E5C46]" title="Restore" data-testid={`admin-vendor-restore-${p.id}`}>
                          <Undo2 size={14} strokeWidth={1.5} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
