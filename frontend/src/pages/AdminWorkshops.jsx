import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ArrowLeft, Plus, Pencil, Copy, XCircle, Search, Calendar, Users, DollarSign } from "lucide-react";
import WorkshopFormDrawer from "../components/admin/WorkshopFormDrawer";

const STATUS_COLORS = {
  draft: "bg-[#E5E1D8] text-[#5C6B6B]",
  upcoming: "bg-[#476B6B]/10 text-[#476B6B]",
  in_progress: "bg-[#C9A961]/15 text-[#C9A961]",
  completed: "bg-[#2E5C46]/10 text-[#2E5C46]",
  cancelled: "bg-[#B86A5C]/10 text-[#B86A5C]",
};

function StatusPill({ status }) {
  return (
    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${STATUS_COLORS[status] || "bg-[#E5E1D8] text-[#5C6B6B]"}`}>
      {status?.replace("_", " ")}
    </span>
  );
}

function WorkshopRow({ workshop, onEdit, onDuplicate, onCancel, onViewRevenue }) {
  const dateLabel = workshop.start_date ? new Date(workshop.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";
  const canCancel = workshop.status !== "cancelled" && workshop.status !== "completed";
  return (
    <tr className="border-b border-[#E5E1D8] last:border-0" data-testid={`ws-row-${workshop.id}`}>
      <td className="p-3">
        <div className="w-20 h-12 bg-[#E5E1D8] rounded overflow-hidden">
          {workshop.image_url ? <img src={workshop.image_url} alt="" className="w-full h-full object-cover" /> : null}
        </div>
      </td>
      <td className="p-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">{workshop.title}</span>
          <StatusPill status={workshop.status} />
        </div>
        <p className="text-xs text-[#5C6B6B] mt-1 line-clamp-1 max-w-md">{workshop.short_description}</p>
      </td>
      <td className="p-3 text-xs text-[#5C6B6B]">
        <div className="inline-flex items-center gap-1"><Calendar size={11} strokeWidth={1.5} />{dateLabel}</div>
      </td>
      <td className="p-3 text-xs">
        <div className="inline-flex items-center gap-1 text-[#5C6B6B]"><Users size={11} strokeWidth={1.5} />{workshop.registered_count ?? 0}/{workshop.capacity}</div>
      </td>
      <td className="p-3">
        <div className="flex items-center gap-2 justify-end">
          <button onClick={() => onViewRevenue(workshop)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]" title="Revenue" data-testid={`ws-revenue-${workshop.id}`}>
            <DollarSign size={14} strokeWidth={1.5} />
          </button>
          <button onClick={() => onEdit(workshop)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]" title="Edit" data-testid={`ws-edit-${workshop.id}`}>
            <Pencil size={14} strokeWidth={1.5} />
          </button>
          <button onClick={() => onDuplicate(workshop)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#476B6B]" title="Duplicate" data-testid={`ws-duplicate-${workshop.id}`}>
            <Copy size={14} strokeWidth={1.5} />
          </button>
          {canCancel && (
            <button onClick={() => onCancel(workshop)} className="p-2 rounded-full hover:bg-[#FAF8F5] text-[#B86A5C]" title="Cancel" data-testid={`ws-cancel-${workshop.id}`}>
              <XCircle size={14} strokeWidth={1.5} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function RevenueModal({ workshop, stats, onClose }) {
  if (!workshop) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" data-testid="ws-revenue-modal">
      <div className="bg-white max-w-md w-full p-7 rounded-sm border border-[#E5E1D8]">
        <p className="label">Revenue</p>
        <h2 className="font-serif text-2xl mt-1">{workshop.title}</h2>
        <div className="divider-flame" />
        {!stats ? (
          <p className="text-sm text-[#5C6B6B] mt-4">Loading...</p>
        ) : (
          <table className="w-full text-sm mt-4">
            <tbody>
              <tr><td className="py-2 text-[#5C6B6B]">Paid registrations</td><td className="text-right">{stats.paid_count} / {stats.capacity}</td></tr>
              <tr><td className="py-2 text-[#5C6B6B]">Cancelled</td><td className="text-right">{stats.cancelled_count}</td></tr>
              <tr><td className="py-2 text-[#5C6B6B]">Checked in</td><td className="text-right">{stats.checked_in_count}</td></tr>
              <tr className="border-t border-[#E5E1D8]"><td className="py-2 text-[#5C6B6B]">Gross revenue</td><td className="text-right font-medium">${stats.gross_revenue.toFixed(2)}</td></tr>
              <tr><td className="py-2 text-[#5C6B6B]">Refunded</td><td className="text-right text-[#B86A5C]">−${stats.refunded.toFixed(2)}</td></tr>
              <tr className="border-t border-[#E5E1D8] font-serif text-lg"><td className="py-3">Net</td><td className="text-right">${stats.net_revenue.toFixed(2)}</td></tr>
            </tbody>
          </table>
        )}
        <button onClick={onClose} className="btn-outline w-full justify-center mt-6" data-testid="ws-revenue-close">Close</button>
      </div>
    </div>
  );
}

export default function AdminWorkshops() {
  const { user } = useAuth();
  const [workshops, setWorkshops] = useState([]);
  const [facilitators, setFacilitators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [revenueWs, setRevenueWs] = useState(null);
  const [revenueStats, setRevenueStats] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/workshops"),
      api.get("/facilitators"),
    ]).then(([wRes, fRes]) => {
      setWorkshops(wRes.data);
      setFacilitators(fRes.data);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const visible = useMemo(() => {
    return workshops.filter((w) => {
      if (statusFilter !== "all" && w.status !== statusFilter) return false;
      if (search.trim()) {
        const s = search.toLowerCase();
        return w.title?.toLowerCase().includes(s) || w.slug?.toLowerCase().includes(s);
      }
      return true;
    });
  }, [workshops, search, statusFilter]);

  const openNew = () => { setEditing(null); setDrawerOpen(true); };
  const openEdit = async (w) => {
    // Fetch full workshop so we get check_in_code (not in public list)
    try {
      const r = await api.get(`/workshops/${w.id}`);
      setEditing(r.data);
    } catch {
      setEditing(w);
    }
    setDrawerOpen(true);
  };
  const duplicate = async (w) => {
    if (!window.confirm(`Duplicate "${w.title}"? A draft copy will be created with dates 30 days in the future.`)) return;
    try {
      await api.post(`/workshops/${w.id}/duplicate`);
      toast.success("Workshop duplicated. Look for the new draft in the list.");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Duplicate failed");
    }
  };
  const cancel = async (w) => {
    const seats = w.registered_count || 0;
    const confirmText = window.prompt(
      `This will CANCEL "${w.title}" and attempt to refund ${seats} paid registration${seats === 1 ? "" : "s"}.\n\nAll registrants will be emailed.\n\nType CANCEL to confirm:`
    );
    if (confirmText !== "CANCEL") return;
    try {
      const res = await api.post(`/workshops/${w.id}/cancel`);
      const r = res.data;
      toast.success(
        `Workshop cancelled. Refunds: ${r.refunds_succeeded} succeeded, ${r.refunds_pending} pending, ${r.refunds_failed} failed.`,
        { duration: 8000 }
      );
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Cancel failed");
    }
  };
  const viewRevenue = async (w) => {
    setRevenueWs(w);
    setRevenueStats(null);
    try {
      const r = await api.get(`/workshops/${w.id}/revenue`);
      setRevenueStats(r.data);
    } catch (err) {
      toast.error("Could not load revenue");
      setRevenueWs(null);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-workshops-page">
      <Link to={user?.role === "admin" ? "/admin" : "/facilitator"} className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="label">Workshops</span>
          <h1 className="editorial-h1 mt-2">Manage workshops</h1>
          <div className="divider-flame" />
          <p className="text-sm text-[#5C6B6B]">{workshops.length} workshop{workshops.length === 1 ? "" : "s"} on the calendar.</p>
        </div>
        <button onClick={openNew} className="btn-primary" data-testid="ws-new-button">
          <Plus size={16} strokeWidth={1.5} /> New workshop
        </button>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-3" data-testid="ws-toolbar">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title or slug..." className="input-field pl-9" data-testid="ws-search" />
        </div>
        <div className="flex gap-1 flex-wrap">
          {["all", "draft", "upcoming", "in_progress", "completed", "cancelled"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-2 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                statusFilter === s ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`ws-filter-${s}`}
            >
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="card mt-6 overflow-x-auto" data-testid="ws-table">
        {loading ? (
          <div className="p-12 text-center text-sm text-[#5C6B6B]">Loading workshops...</div>
        ) : visible.length === 0 ? (
          <div className="p-12 text-center">
            <Calendar size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
            <p className="font-serif text-lg mt-3">Nothing matches.</p>
            <p className="text-sm text-[#5C6B6B] mt-1">
              {search || statusFilter !== "all" ? "Try a different filter." : "Create your first workshop."}
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[#FAF8F5] border-b border-[#E5E1D8]">
              <tr>
                <th className="p-3 text-left label w-24">Image</th>
                <th className="p-3 text-left label">Workshop</th>
                <th className="p-3 text-left label">Date</th>
                <th className="p-3 text-left label">Seats</th>
                <th className="p-3 text-right label">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((w) => (
                <WorkshopRow key={w.id} workshop={w} onEdit={openEdit} onDuplicate={duplicate} onCancel={cancel} onViewRevenue={viewRevenue} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <WorkshopFormDrawer
        open={drawerOpen}
        initial={editing}
        facilitators={facilitators}
        currentUser={user}
        onClose={() => setDrawerOpen(false)}
        onSaved={load}
      />
      {revenueWs && <RevenueModal workshop={revenueWs} stats={revenueStats} onClose={() => setRevenueWs(null)} />}
    </div>
  );
}
