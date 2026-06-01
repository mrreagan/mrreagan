import React, { useEffect, useState, useMemo } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { Users, Calendar, ShoppingBag, DollarSign, Heart, Mail, Gem, Camera, Scale, Briefcase, BarChart3, Wallet, Store, UserPlus, ExternalLink, Sparkles, Shield, RotateCcw, Microscope, Bot, FlaskConical, Server, FileText } from "lucide-react";
import { toast } from "sonner";

// ---------- Stat card ----------
function StatCard({ icon: Icon, value, label }) {
  return (
    <div className="card p-5">
      <Icon size={18} strokeWidth={1.5} className="text-[#C9A961]" />
      <p className="font-serif text-3xl text-[#1A2424] mt-3">{value}</p>
      <p className="label mt-1">{label}</p>
    </div>
  );
}

// ---------- Stats grid ----------
function StatsGrid({ stats }) {
  const items = useMemo(
    () => [
      { label: "Users", value: stats.users_count, icon: Users },
      { label: "Workshops", value: stats.workshops_count, icon: Calendar },
      { label: "Registrations", value: stats.registrations_count, icon: Heart },
      { label: "Orders", value: stats.orders_count, icon: ShoppingBag },
      { label: "Products", value: stats.products_count, icon: ShoppingBag },
      { label: "Newsletter", value: stats.newsletter_count, icon: Mail },
      { label: "Sponsors", value: stats.sponsors_count, icon: Gem },
      { label: "Revenue", value: `$${(stats.total_revenue || 0).toFixed(0)}`, icon: DollarSign },
    ],
    [stats]
  );
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8" data-testid="admin-stats">
      {items.map((s) => (
        <StatCard key={s.label} icon={s.icon} value={s.value} label={s.label} />
      ))}
    </div>
  );
}

// ---------- Quick action card ----------
function QuickActionCard({ to, icon: Icon, title, description }) {
  return (
    <Link to={to} className="card card-hover p-7">
      <Icon size={22} strokeWidth={1.5} className="text-[#C9A961]" />
      <h3 className="font-serif text-xl mt-3">{title}</h3>
      <p className="text-sm text-[#5C6B6B] mt-2">{description}</p>
    </Link>
  );
}

// ---------- Overview tab ----------
function OverviewTab() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5" data-testid="admin-overview">
      <QuickActionCard to="/admin/workshops" icon={Calendar} title="Manage Workshops" description="Create, edit, cancel, duplicate" />
      <QuickActionCard to="/admin/products" icon={ShoppingBag} title="Manage Products" description="Merch and workshop materials" />
      <QuickActionCard to="/admin/photos" icon={Camera} title="Photo Moderation" description="Approve participant uploads" />
      <QuickActionCard to="/admin/governance" icon={Scale} title="Governance & Legal" description="Defaults, members, indemnification, audit" />
      <QuickActionCard to="/admin/partners" icon={Briefcase} title="Partner applications" description="Approve, reject, invite partners" />
      <QuickActionCard to="/admin/partners/prospects" icon={Briefcase} title="Partner prospects (all types)" description="Outreach tracker · Explore-before-Embrace invitations" />
      <QuickActionCard to="/admin/gallery/prospects" icon={Briefcase} title="Featured Artist prospects" description="Track outreach · issue Foundation invitations" />
      <QuickActionCard to="/admin/foundation-roles" icon={UserPlus} title="Foundation roles" description="Open board seats & job descriptions" />
      <QuickActionCard to="/admin/foundation-applications" icon={UserPlus} title="Role applications" description="Triage applicants for open board seats" />
      <QuickActionCard to="/admin/vendor-products" icon={Store} title="Vendor catalog" description="Moderate vendor-submitted products" />
      <QuickActionCard to="/admin/studio/queue" icon={FlaskConical} title="Studio queue" description="Approve vendor AI Studio submissions" />
      <QuickActionCard to="/admin/lulu-ops" icon={Server} title="Lulu cutover" description="Validate POD presets · manage webhooks" />
      <QuickActionCard to="/admin/email-ops" icon={Mail} title="Email cutover" description="Resend status · flip dry-run → live" />
      <QuickActionCard to="/admin/payouts" icon={Wallet} title="Partner payouts" description="Referral ledger & disbursements" />
      <QuickActionCard to="/admin/subscriptions" icon={Wallet} title="Subscriptions" description="Active, cancelled, revoke + refund" />
      <QuickActionCard to="/admin/ombudsman" icon={Shield} title="Ombudsman queue" description="Disputes + flagged DM threads" />
      <QuickActionCard to="/admin/refunds" icon={RotateCcw} title="Refunds & Clawbacks" description="Fire refund cascades, resolve clawbacks" />
      <QuickActionCard to="/admin/research" icon={Microscope} title="Research moderation" description="Approve, request changes, reject submissions" />
      <QuickActionCard to="/admin/ai-usage" icon={Bot} title="AI usage" description="Per-partner AI spend + wallet balances" />
      <QuickActionCard to="/admin/legal/agreements" icon={FileText} title="Partnership agreements" description="Publish, audit, and gate write-features" />
      <QuickActionCard to="/admin/partner-sales-reports" icon={ExternalLink} title="Off-site sales reports" description="Reconcile partner-reported revenue" />
      <QuickActionCard to="/admin/featured" icon={Sparkles} title="Featured & Founding" description="Grant/revoke featured slots, founding-partner cap" />
      <QuickActionCard to="/admin/reports" icon={BarChart3} title="Foundation reports" description="Engagement, revenue, payouts" />
      <QuickActionCard to="/admin/content" icon={Heart} title="Foundation Content" description="Mission, about, governance" />
    </div>
  );
}

// ---------- Users tab ----------
function UsersTab({ users, onChangeRole }) {
  return (
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
              <td className="p-4">
                {u.first_name} {u.last_name}
              </td>
              <td className="p-4 text-[#5C6B6B]">{u.email}</td>
              <td className="p-4">
                <select
                  value={u.role}
                  onChange={(e) => onChangeRole(u.id, e.target.value)}
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
  );
}

// ---------- Messages tab ----------
function MessagesTab({ messages }) {
  if (messages.length === 0) {
    return <p className="text-sm text-[#5C6B6B]" data-testid="admin-messages">No messages.</p>;
  }
  return (
    <div className="space-y-3" data-testid="admin-messages">
      {messages.map((m) => (
        <div key={m.id} className="card p-5">
          <div className="flex items-center justify-between">
            <p className="font-medium">
              {m.first_name} {m.last_name || ""}
            </p>
            <p className="text-xs text-[#5C6B6B]">{new Date(m.created_at).toLocaleDateString()}</p>
          </div>
          <p className="text-xs text-[#5C6B6B] mt-1">
            {m.email} · {m.phone}
          </p>
          <p className="text-xs text-[#C9A961] uppercase tracking-wider mt-2">{m.subject}</p>
          <p className="text-sm mt-2 whitespace-pre-line">{m.message}</p>
        </div>
      ))}
    </div>
  );
}

// ---------- Email log tab ----------
function EmailLogTab({ items, realSendEnabled }) {
  return (
    <div data-testid="admin-email-log">
      <div className={`card p-4 mb-4 ${realSendEnabled ? "bg-[#F0F6F4]" : "bg-[#FFF8E8]"}`}>
        <p className="text-sm">
          {realSendEnabled ? (
            <>
              <strong className="text-[#2E5C46]">Live mode.</strong>{" "}
              Emails are sending through Resend to real inboxes.
            </>
          ) : (
            <>
              <strong className="text-[#C9A961]">Dry-run mode.</strong>{" "}
              Emails are queued for inspection only — no real sends. Add a valid <code>RESEND_API_KEY</code>{" "}
              and set <code>EMAIL_DRY_RUN=false</code> in <code>backend/.env</code> to go live.
            </>
          )}
        </p>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-[#5C6B6B]">No emails sent yet.</p>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#FAF8F5] border-b border-[#E5E1D8]">
              <tr>
                <th className="text-left p-3 label">When</th>
                <th className="text-left p-3 label">Template</th>
                <th className="text-left p-3 label">Subject</th>
                <th className="text-left p-3 label">To</th>
                <th className="text-left p-3 label">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-b border-[#E5E1D8] last:border-0" data-testid={`email-row-${e.id}`}>
                  <td className="p-3 text-xs text-[#5C6B6B]">{new Date(e.created_at).toLocaleString()}</td>
                  <td className="p-3 text-xs">{e.template || "—"}</td>
                  <td className="p-3 text-xs">{e.subject}</td>
                  <td className="p-3 text-xs text-[#5C6B6B]">{(e.to || []).join(", ")}</td>
                  <td className="p-3">
                    <span
                      className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        e.status === "sent"
                          ? "bg-[#2E5C46]/10 text-[#2E5C46]"
                          : e.status === "failed"
                          ? "bg-[#B86A5C]/10 text-[#B86A5C]"
                          : "bg-[#C9A961]/15 text-[#C9A961]"
                      }`}
                    >
                      {e.status?.replace("_", " ") || "queued"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------- Tab switcher ----------
const TABS = [
  { id: "overview", label: "Overview" },
  { id: "users", label: "Users" },
  { id: "messages", label: "Contact Messages" },
  { id: "emails", label: "Email log" },
];

function TabBar({ active, onChange }) {
  return (
    <div className="mt-10 border-b border-[#E5E1D8] flex gap-1 overflow-x-auto no-scrollbar">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
            active === t.id ? "border-[#476B6B] text-[#476B6B]" : "border-transparent text-[#5C6B6B] hover:text-[#1A2424]"
          }`}
          data-testid={`admin-tab-${t.id}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ---------- Main component ----------
export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [messages, setMessages] = useState([]);
  const [emailLog, setEmailLog] = useState({ items: [], real_send_enabled: false });
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    api.get("/dashboard/admin").then((r) => setStats(r.data));
    api.get("/admin/users").then((r) => setUsers(r.data));
    api.get("/contact/messages").then((r) => setMessages(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "emails") {
      api.get("/admin/email-log?limit=100").then((r) => setEmailLog(r.data)).catch(() => {});
    }
  }, [tab]);

  const changeRole = async (userId, role) => {
    await api.put(`/admin/users/${userId}/role`, { role });
    setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role } : u)));
    toast.success(`Role updated to ${role}`);
  };

  if (!stats) {
    return (
      <div className="container-page py-20" data-testid="admin-loading">
        Loading...
      </div>
    );
  }

  return (
    <div className="container-page py-12" data-testid="admin-dashboard-page">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Foundation overview</h1>
      <div className="divider-flame" />
      <StatsGrid stats={stats} />
      <TabBar active={tab} onChange={setTab} />
      <div className="mt-8">
        {tab === "overview" && <OverviewTab />}
        {tab === "users" && <UsersTab users={users} onChangeRole={changeRole} />}
        {tab === "messages" && <MessagesTab messages={messages} />}
        {tab === "emails" && <EmailLogTab items={emailLog.items} realSendEnabled={emailLog.real_send_enabled} />}
      </div>
    </div>
  );
}
