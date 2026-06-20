/* eslint-disable */
import React, { useEffect, useMemo, useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Search, Shield, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get("/admin/users");
      setUsers(res.data || []);
    } catch (err) {
      toast.error("Could not load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return users
      .filter((u) => {
        if (filter === "foundation" && !u.is_foundation) return false;
        if (filter === "admin" && u.role !== "admin") return false;
        if (!needle) return true;
        return (
          (u.email || "").toLowerCase().includes(needle) ||
          (u.first_name || "").toLowerCase().includes(needle) ||
          (u.last_name || "").toLowerCase().includes(needle)
        );
      });
  }, [users, q, filter]);

  const toggleFoundation = async (u, next) => {
    try {
      await api.patch(`/admin/users/${u.id}/foundation-status`, { is_foundation: next });
      setUsers((cur) => cur.map((x) => (x.id === u.id ? { ...x, is_foundation: next } : x)));
      toast.success(`${u.email}: ${next ? "marked as foundation member" : "removed from foundation membership"}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Update failed");
    }
  };

  const foundationCount = users.filter((u) => u.is_foundation).length;

  return (
    <div className="container max-w-6xl py-10" data-testid="admin-users-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-xs text-[#476B6B] hover:underline mb-6">
        <ArrowLeft size={12} strokeWidth={1.5} /> Admin hub
      </Link>
      <header className="flex items-baseline justify-between flex-wrap gap-4 mb-6">
        <div>
          <span className="label text-[#C9A961]">Admin</span>
          <h1 className="font-serif text-3xl mt-1">Users & members</h1>
          <p className="text-sm text-[#5C6B6B] mt-2 max-w-prose">
            Toggle the <strong>Foundation member</strong> flag to unlock wholesale pricing on equip products and 1:1 passthrough on AI wallet usage. Reserve this for board members, paid staff, and officers.
          </p>
        </div>
        <div className="text-right">
          <p className="font-serif text-3xl text-[#1A2424]">{foundationCount}</p>
          <p className="label">Foundation members</p>
        </div>
      </header>

      <div className="flex items-center gap-3 flex-wrap mb-5">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input
            type="search"
            className="input-field pl-9"
            placeholder="Search name or email"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            data-testid="admin-users-search"
          />
        </div>
        <div className="flex items-center gap-2">
          {[
            { v: "all", label: "All" },
            { v: "foundation", label: "Foundation" },
            { v: "admin", label: "Admin" },
          ].map((f) => (
            <button
              key={f.v}
              onClick={() => setFilter(f.v)}
              className={`px-3 py-1.5 rounded-full text-xs uppercase tracking-wider border transition ${
                filter === f.v
                  ? "bg-[#1A2424] text-[#FAF8F5] border-[#1A2424]"
                  : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`admin-users-filter-${f.v}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card overflow-x-auto">
        {loading ? (
          <p className="p-6 text-sm text-[#5C6B6B]">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E1D8] text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                <th className="p-3 text-left">Email</th>
                <th className="p-3 text-left">Name</th>
                <th className="p-3 text-left">Role</th>
                <th className="p-3 text-left">Foundation</th>
                <th className="p-3 text-left">Joined</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="border-b border-[#E5E1D8] last:border-0" data-testid={`user-row-${u.id}`}>
                  <td className="p-3 font-mono text-xs">{u.email}</td>
                  <td className="p-3">{[u.first_name, u.last_name].filter(Boolean).join(" ") || "—"}</td>
                  <td className="p-3">
                    {u.role === "admin" ? (
                      <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-semibold text-[#2C4E5A]">
                        <Shield size={11} strokeWidth={1.5} /> admin
                      </span>
                    ) : (
                      <span className="text-xs text-[#5C6B6B]">{u.role || "member"}</span>
                    )}
                  </td>
                  <td className="p-3">
                    <label className="inline-flex items-center gap-2 cursor-pointer" data-testid={`user-foundation-toggle-${u.id}`}>
                      <input
                        type="checkbox"
                        checked={!!u.is_foundation}
                        onChange={(e) => toggleFoundation(u, e.target.checked)}
                        className="w-4 h-4 accent-[#C9A961]"
                      />
                      {u.is_foundation && (
                        <span className="text-[10px] uppercase tracking-wider font-semibold text-[#C9A961]">wholesale + 1:1 AI</span>
                      )}
                    </label>
                  </td>
                  <td className="p-3 text-xs text-[#5C6B6B]">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-sm text-[#5C6B6B]">No users match this filter.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
