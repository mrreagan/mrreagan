import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { Users, Calendar, ShoppingBag, DollarSign, Heart, Mail, Gem } from "lucide-react";
import { toast } from "sonner";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [messages, setMessages] = useState([]);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    api.get("/dashboard/admin").then((r) => setStats(r.data));
    api.get("/admin/users").then((r) => setUsers(r.data));
    api.get("/contact/messages").then((r) => setMessages(r.data)).catch(() => {});
  }, []);

  const changeRole = async (userId, role) => {
    await api.put(`/admin/users/${userId}/role`, { role });
    setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role } : u)));
    toast.success(`Role updated to ${role}`);
  };

  if (!stats) return <div className="container-page py-20" data-testid="admin-loading">Loading...</div>;

  const STATS = [
    { label: "Users", value: stats.users_count, icon: Users },
    { label: "Workshops", value: stats.workshops_count, icon: Calendar },
    { label: "Registrations", value: stats.registrations_count, icon: Heart },
    { label: "Orders", value: stats.orders_count, icon: ShoppingBag },
    { label: "Products", value: stats.products_count, icon: ShoppingBag },
    { label: "Newsletter", value: stats.newsletter_count, icon: Mail },
    { label: "Sponsors", value: stats.sponsors_count, icon: Gem },
    { label: "Revenue", value: `$${(stats.total_revenue || 0).toFixed(0)}`, icon: DollarSign },
  ];

  return (
    <div className="container-page py-12" data-testid="admin-dashboard-page">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Foundation overview</h1>
      <div className="divider-flame" />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8" data-testid="admin-stats">
        {STATS.map((s) => (
          <div key={s.label} className="card p-5">
            <s.icon size={18} strokeWidth={1.5} className="text-[#C9A961]" />
            <p className="font-serif text-3xl text-[#1A2424] mt-3">{s.value}</p>
            <p className="label mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 border-b border-[#E5E1D8] flex gap-1 overflow-x-auto no-scrollbar">
        {[
          { id: "overview", label: "Overview" },
          { id: "users", label: "Users" },
          { id: "messages", label: "Contact Messages" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
              tab === t.id ? "border-[#476B6B] text-[#476B6B]" : "border-transparent text-[#5C6B6B] hover:text-[#1A2424]"
            }`}
            data-testid={`admin-tab-${t.id}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {tab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5" data-testid="admin-overview">
            <Link to="/admin/workshops" className="card card-hover p-7">
              <Calendar size={22} strokeWidth={1.5} className="text-[#C9A961]" />
              <h3 className="font-serif text-xl mt-3">Manage Workshops</h3>
              <p className="text-sm text-[#5C6B6B] mt-2">Create, edit, schedule</p>
            </Link>
            <Link to="/admin/products" className="card card-hover p-7">
              <ShoppingBag size={22} strokeWidth={1.5} className="text-[#C9A961]" />
              <h3 className="font-serif text-xl mt-3">Manage Products</h3>
              <p className="text-sm text-[#5C6B6B] mt-2">Merch and workshop materials</p>
            </Link>
            <Link to="/admin/content" className="card card-hover p-7">
              <Heart size={22} strokeWidth={1.5} className="text-[#C9A961]" />
              <h3 className="font-serif text-xl mt-3">Foundation Content</h3>
              <p className="text-sm text-[#5C6B6B] mt-2">Mission, about, governance</p>
            </Link>
          </div>
        )}

        {tab === "users" && (
          <div className="card overflow-hidden" data-testid="admin-users-table">
            <table className="w-full text-sm">
              <thead className="bg-[#FAF8F5] border-b border-[#E5E1D8]">
                <tr>
                  <th className="text-left p-4 label">Name</th>
                  <th className="text-left p-4 label">Email</th>
                  <th className="text-left p-4 label">Role</th>
                  <th className="text-left p-4 label">Joined</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-[#E5E1D8] last:border-0">
                    <td className="p-4">{u.first_name} {u.last_name}</td>
                    <td className="p-4 text-[#5C6B6B]">{u.email}</td>
                    <td className="p-4">
                      <select
                        value={u.role}
                        onChange={(e) => changeRole(u.id, e.target.value)}
                        className="input-field !py-1 text-xs"
                        data-testid={`user-role-${u.id}`}
                      >
                        <option value="participant">Participant</option>
                        <option value="facilitator">Facilitator</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="p-4 text-[#5C6B6B] text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === "messages" && (
          <div className="space-y-3" data-testid="admin-messages">
            {messages.length === 0 && <p className="text-sm text-[#5C6B6B]">No messages.</p>}
            {messages.map((m) => (
              <div key={m.id} className="card p-5">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{m.first_name} {m.last_name || ""}</p>
                  <p className="text-xs text-[#5C6B6B]">{new Date(m.created_at).toLocaleDateString()}</p>
                </div>
                <p className="text-xs text-[#5C6B6B] mt-1">{m.email} · {m.phone}</p>
                <p className="text-xs text-[#C9A961] uppercase tracking-wider mt-2">{m.subject}</p>
                <p className="text-sm mt-2 whitespace-pre-line">{m.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
