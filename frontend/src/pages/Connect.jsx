import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Hash, Lock, Users, Send, Calendar, Plus, ChevronLeft, ExternalLink, Circle,
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

// ---------------------------------------------------------------------------
// WebSocket helpers
// ---------------------------------------------------------------------------
function wsUrlFor(channelId) {
  const base = process.env.REACT_APP_BACKEND_URL || window.location.origin;
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}/api/ws/connect/${channelId}`;
}

// ---------------------------------------------------------------------------
// Top-level page
// ---------------------------------------------------------------------------
export default function Connect() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [channels, setChannels] = useState([]);
  const [active, setActive] = useState(null); // channel id
  const [loadingChannels, setLoadingChannels] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (!loading && !user) navigate("/login", { replace: true });
  }, [user, loading, navigate]);

  const refreshChannels = useCallback(async () => {
    try {
      const r = await api.get("/connect/channels");
      setChannels(r.data);
      if (r.data.length && !active) setActive(r.data[0].id);
    } catch (e) {
      if (e?.response?.status !== 401) toast.error("Couldn’t load channels");
    } finally {
      setLoadingChannels(false);
    }
  }, [active]);

  useEffect(() => { if (user) refreshChannels(); }, [user, refreshChannels]);

  if (loading || !user) {
    return <p className="container-page py-20 text-sm text-[#5C6B6B]">Loading…</p>;
  }

  const activeChannel = channels.find((c) => c.id === active);

  return (
    <div className="container-page py-8" data-testid="connect-page">
      <div className="flex items-baseline justify-between flex-wrap gap-3 mb-4">
        <div>
          <span className="label">Connect</span>
          <h1 className="editorial-h1 mt-2">Channels, conversations, meetings.</h1>
          <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
            A Teams-style space for the Birthright community. Open channels are visible to all signed-in members;
            private channels are limited by role.
          </p>
        </div>
        {user?.role === "admin" && (
          <NewChannelButton onCreated={refreshChannels} />
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-0 md:gap-4 border border-[#E5E1D8] rounded-2xl overflow-hidden bg-white" style={{ minHeight: "70vh" }}>
        {/* ----- Sidebar ----- */}
        {(sidebarOpen || !active) && (
          <aside className="md:col-span-3 border-b md:border-b-0 md:border-r border-[#E5E1D8] bg-[#FAF8F5]" data-testid="connect-sidebar">
            <div className="p-4">
              <p className="label !mt-0 mb-3">Channels</p>
              {loadingChannels ? (
                <p className="text-xs text-[#5C6B6B]">Loading…</p>
              ) : channels.length === 0 ? (
                <p className="text-xs text-[#5C6B6B]">No channels yet.</p>
              ) : (
                <ul className="space-y-1">
                  {channels.map((c) => (
                    <ChannelRow
                      key={c.id}
                      channel={c}
                      active={active === c.id}
                      onClick={() => {
                        setActive(c.id);
                        // Only collapse on mobile; on desktop keep both panes visible.
                        if (window.innerWidth < 768) setSidebarOpen(false);
                      }}
                    />
                  ))}
                </ul>
              )}
            </div>
          </aside>
        )}

        {/* ----- Main pane ----- */}
        <section className={`md:col-span-9 flex flex-col ${sidebarOpen ? "hidden md:flex" : "flex"}`} data-testid="connect-main">
          {activeChannel ? (
            <ChannelPane
              channel={activeChannel}
              currentUser={user}
              onBack={() => setSidebarOpen(true)}
              onMeetingChanged={refreshChannels}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-[#5C6B6B] p-8 text-center">
              Pick a channel from the sidebar to start chatting.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar channel row
// ---------------------------------------------------------------------------
function ChannelRow({ channel, active, onClick }) {
  const Icon = channel.type === "public" ? Hash : Lock;
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition ${
          active ? "bg-white shadow-sm text-[#1A2424]" : "hover:bg-white text-[#1A2424]"
        }`}
        data-testid={`connect-channel-row-${channel.slug}`}
      >
        <Icon size={14} strokeWidth={1.5} className="text-[#5C6B6B] shrink-0" />
        <span className="flex-1 truncate font-medium">{channel.name}</span>
        {channel.is_announcement_only && (
          <span className="text-[9px] uppercase tracking-wider text-[#C9A961]">A</span>
        )}
      </button>
    </li>
  );
}

// ---------------------------------------------------------------------------
// New channel modal (admin)
// ---------------------------------------------------------------------------
function NewChannelButton({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "", slug: "", description: "",
    type: "public", role_required: "all", is_announcement_only: false,
  });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.slug.trim()) {
      toast.error("Name and slug are required");
      return;
    }
    setBusy(true);
    try {
      await api.post("/connect/channels", {
        ...form,
        slug: form.slug.trim().toLowerCase().replace(/[^a-z0-9-]+/g, "-"),
      });
      toast.success("Channel created");
      setOpen(false);
      setForm({ name: "", slug: "", description: "", type: "public", role_required: "all", is_announcement_only: false });
      onCreated?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn’t create channel");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="connect-new-channel-btn">
        <Plus size={14} strokeWidth={1.5} /> New channel
      </button>
      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <form
            onSubmit={submit}
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-2xl p-6 w-full max-w-md flex flex-col gap-3"
            data-testid="connect-new-channel-modal"
          >
            <h2 className="font-serif text-2xl">New channel</h2>
            <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
              Name
              <input className="input-field mt-1" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="connect-channel-name" />
            </label>
            <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
              Slug
              <input className="input-field mt-1" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} placeholder="e.g. alumni-2026" data-testid="connect-channel-slug" />
            </label>
            <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
              Description
              <textarea className="input-field mt-1 min-h-[60px]" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="connect-channel-desc" />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                Type
                <select className="input-field mt-1" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} data-testid="connect-channel-type">
                  <option value="public">Public</option>
                  <option value="role_gated">Role-gated</option>
                </select>
              </label>
              <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                Role
                <select
                  className="input-field mt-1"
                  value={form.role_required}
                  onChange={(e) => setForm({ ...form, role_required: e.target.value })}
                  disabled={form.type === "public"}
                  data-testid="connect-channel-role"
                >
                  <option value="all">All</option>
                  <option value="facilitators">Facilitators</option>
                  <option value="partners">Partners</option>
                  <option value="alumni">Alumni</option>
                  <option value="admins">Admins</option>
                </select>
              </label>
            </div>
            <label className="text-xs flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_announcement_only}
                onChange={(e) => setForm({ ...form, is_announcement_only: e.target.checked })}
                data-testid="connect-channel-announce"
              />
              Announcement-only (admins post, everyone reads)
            </label>
            <div className="flex gap-2 mt-2">
              <button type="submit" disabled={busy} className="btn-primary text-sm flex-1" data-testid="connect-channel-submit">
                {busy ? "Creating…" : "Create channel"}
              </button>
              <button type="button" onClick={() => setOpen(false)} className="btn-outline text-sm">Cancel</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Channel pane — messages + meetings tabs
// ---------------------------------------------------------------------------
function ChannelPane({ channel, currentUser, onBack, onMeetingChanged }) {
  const [tab, setTab] = useState("chat");
  const [messages, setMessages] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [online, setOnline] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showMeetingForm, setShowMeetingForm] = useState(false);
  const scrollRef = useRef(null);
  const wsRef = useRef(null);
  const Icon = channel.type === "public" ? Hash : Lock;
  const canPost = !channel.is_announcement_only || currentUser?.role === "admin";

  // Load messages whenever channel changes
  useEffect(() => {
    let cancelled = false;
    setMessages([]);
    api.get(`/connect/channels/${channel.id}/messages`).then((r) => { if (!cancelled) setMessages(r.data); }).catch(() => {});
    api.get(`/connect/channels/${channel.id}/meetings`).then((r) => { if (!cancelled) setMeetings(r.data); }).catch(() => {});
    return () => { cancelled = true; };
  }, [channel.id]);

  // Open WebSocket for real-time updates
  useEffect(() => {
    const ws = new WebSocket(wsUrlFor(channel.id));
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "chat" && data.message) {
          setMessages((m) => {
            if (m.some((mm) => mm.id === data.message.id)) return m;
            return [...m, data.message];
          });
        } else if (data.type === "presence" && Array.isArray(data.users)) {
          setOnline(data.users);
        }
      } catch { /* ignore malformed */ }
    };
    ws.onerror = () => { /* swallow */ };
    return () => { try { ws.close(); } catch { /* noop */ } };
  }, [channel.id]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      const r = await api.post(`/connect/channels/${channel.id}/messages`, { content: text });
      setInput("");
      setMessages((m) => (m.some((mm) => mm.id === r.data.id) ? m : [...m, r.data]));
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn’t send message");
    } finally {
      setBusy(false);
    }
  };

  const onMeetingCreated = (m) => {
    setMeetings((arr) => [...arr, m]);
    setShowMeetingForm(false);
    onMeetingChanged?.();
  };

  return (
    <div className="flex flex-col h-full" data-testid={`connect-channel-pane-${channel.slug}`}>
      {/* ----- Header ----- */}
      <header className="px-4 md:px-6 py-3 border-b border-[#E5E1D8] flex items-center gap-3">
        <button onClick={onBack} className="md:hidden text-[#5C6B6B]" aria-label="Back to channels" data-testid="connect-back-btn">
          <ChevronLeft size={18} strokeWidth={1.5} />
        </button>
        <Icon size={16} strokeWidth={1.5} className="text-[#5C6B6B]" />
        <div className="flex-1 min-w-0">
          <p className="font-serif text-lg leading-tight truncate" data-testid="connect-channel-title">{channel.name}</p>
          {channel.description && (
            <p className="text-xs text-[#5C6B6B] truncate">{channel.description}</p>
          )}
        </div>
        <div className="hidden md:flex items-center gap-1 text-[11px] text-[#5C6B6B]">
          <Users size={12} strokeWidth={1.5} /> {online.length} online
        </div>
      </header>

      {/* ----- Tab switcher ----- */}
      <nav className="flex border-b border-[#E5E1D8] px-3 md:px-4" data-testid="connect-tabs">
        {["chat", "meetings"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-xs uppercase tracking-wider font-medium border-b-2 transition ${
              tab === t ? "border-[#476B6B] text-[#1A2424]" : "border-transparent text-[#5C6B6B] hover:text-[#1A2424]"
            }`}
            data-testid={`connect-tab-${t}`}
          >
            {t === "chat" ? "Chat" : `Meetings (${meetings.length})`}
          </button>
        ))}
      </nav>

      {tab === "chat" ? (
        <>
          {/* ----- Messages list ----- */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-3" data-testid="connect-messages">
            {messages.length === 0 ? (
              <p className="text-xs text-[#5C6B6B] text-center py-6">No messages yet — be the first to say hello.</p>
            ) : (
              messages.map((m) => <MessageBubble key={m.id} m={m} isSelf={m.sender_id === currentUser?.id} />)
            )}
          </div>

          {/* ----- Composer ----- */}
          <form
            onSubmit={send}
            className="border-t border-[#E5E1D8] p-3 flex gap-2 bg-white pb-[max(0.75rem,env(safe-area-inset-bottom))]"
            data-testid="connect-composer"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={canPost ? `Message #${channel.slug}` : "This channel is announcement-only."}
              className="input-field flex-1 text-sm"
              disabled={!canPost || busy}
              data-testid="connect-message-input"
            />
            <button
              type="submit"
              disabled={!canPost || busy || !input.trim()}
              className="btn-primary px-3"
              data-testid="connect-send-btn"
              aria-label="Send"
            >
              <Send size={14} strokeWidth={1.5} />
            </button>
          </form>
        </>
      ) : (
        <MeetingsTab
          channel={channel}
          meetings={meetings}
          onCreate={() => setShowMeetingForm(true)}
          showForm={showMeetingForm}
          onClose={() => setShowMeetingForm(false)}
          onMeetingCreated={onMeetingCreated}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------
function MessageBubble({ m, isSelf }) {
  const when = useMemo(() => {
    try { return new Date(m.created_at).toLocaleString(); } catch { return ""; }
  }, [m.created_at]);
  return (
    <div className={`flex flex-col ${isSelf ? "items-end" : "items-start"}`} data-testid={`connect-msg-${m.id}`}>
      <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
        isSelf ? "bg-[#476B6B] text-white" : "bg-[#F4F1EA] text-[#1A2424]"
      }`}>
        {!isSelf && <p className="text-[10px] uppercase tracking-wider opacity-70 mb-0.5">{m.sender_name}</p>}
        <p className="whitespace-pre-wrap">{m.content}</p>
        {m.meeting_id && (
          <a
            href={`/connect/meetings/${m.meeting_id}/ics`}
            onClick={(e) => { e.preventDefault(); downloadIcs(m.meeting_id); }}
            className={`mt-1 inline-flex items-center gap-1 text-[11px] underline ${isSelf ? "text-[#FAF8F5]" : "text-[#476B6B]"}`}
            data-testid={`connect-meeting-ics-${m.meeting_id}`}
          >
            <Calendar size={11} /> Add to calendar
          </a>
        )}
      </div>
      <p className="text-[10px] text-[#5C6B6B] mt-0.5 px-1">{when}</p>
    </div>
  );
}

async function downloadIcs(meetingId) {
  try {
    const res = await api.get(`/connect/meetings/${meetingId}/ics`, { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/calendar" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${meetingId}.ics`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    toast.error("Couldn’t download calendar invite");
  }
}

// ---------------------------------------------------------------------------
// Meetings tab
// ---------------------------------------------------------------------------
function MeetingsTab({ channel, meetings, onCreate, showForm, onClose, onMeetingCreated }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6" data-testid="connect-meetings-tab">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg">Meetings in #{channel.slug}</h3>
        <button onClick={onCreate} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="connect-new-meeting-btn">
          <Plus size={14} strokeWidth={1.5} /> Schedule meeting
        </button>
      </div>

      {showForm && (
        <NewMeetingForm channelId={channel.id} onClose={onClose} onCreated={onMeetingCreated} />
      )}

      {meetings.length === 0 ? (
        <p className="text-sm text-[#5C6B6B]">No meetings scheduled yet.</p>
      ) : (
        <ul className="space-y-3">
          {meetings.map((m) => <MeetingRow key={m.id} m={m} />)}
        </ul>
      )}
    </div>
  );
}

function MeetingRow({ m }) {
  const start = useMemo(() => { try { return new Date(m.start_iso).toLocaleString(); } catch { return m.start_iso; } }, [m.start_iso]);
  const end = useMemo(() => { try { return new Date(m.end_iso).toLocaleString(); } catch { return m.end_iso; } }, [m.end_iso]);
  return (
    <li className="card p-4" data-testid={`connect-meeting-row-${m.id}`}>
      <div className="flex items-start gap-3">
        <Calendar size={18} strokeWidth={1.4} className="text-[#C9A961] mt-1 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="font-serif text-base leading-tight">{m.title}</p>
          <p className="text-xs text-[#5C6B6B] mt-1">{start} → {end}</p>
          {m.location && <p className="text-xs text-[#5C6B6B] mt-0.5">📍 {m.location}</p>}
          {m.description && <p className="text-sm text-[#1A2424] mt-2 whitespace-pre-wrap">{m.description}</p>}
          <p className="text-[10px] text-[#5C6B6B] mt-2">Organized by {m.organizer_name || "a member"}</p>
        </div>
        <button onClick={() => downloadIcs(m.id)} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`connect-meeting-download-${m.id}`}>
          <ExternalLink size={12} /> .ics
        </button>
      </div>
    </li>
  );
}

function NewMeetingForm({ channelId, onClose, onCreated }) {
  const today = new Date();
  const inOneHour = new Date(today.getTime() + 60 * 60 * 1000);
  const toLocal = (d) => {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const [form, setForm] = useState({
    title: "",
    description: "",
    start_local: toLocal(inOneHour),
    end_local: toLocal(new Date(inOneHour.getTime() + 60 * 60 * 1000)),
    location: "",
  });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) { toast.error("Title is required"); return; }
    setBusy(true);
    try {
      const r = await api.post(`/connect/channels/${channelId}/meetings`, {
        title: form.title.trim(),
        description: form.description.trim(),
        start_iso: new Date(form.start_local).toISOString(),
        end_iso: new Date(form.end_local).toISOString(),
        location: form.location.trim(),
      });
      toast.success("Meeting scheduled");
      onCreated?.(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn’t create meeting");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="card p-4 mb-4 flex flex-col gap-3" data-testid="connect-new-meeting-form">
      <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
        Title
        <input className="input-field mt-1" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="meeting-title" />
      </label>
      <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
        Description (optional)
        <textarea className="input-field mt-1 min-h-[60px]" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="meeting-desc" />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          Start
          <input type="datetime-local" className="input-field mt-1" value={form.start_local} onChange={(e) => setForm({ ...form, start_local: e.target.value })} data-testid="meeting-start" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          End
          <input type="datetime-local" className="input-field mt-1" value={form.end_local} onChange={(e) => setForm({ ...form, end_local: e.target.value })} data-testid="meeting-end" />
        </label>
      </div>
      <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
        Location / link
        <input className="input-field mt-1" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="e.g. Zoom link, address, or 'TBD'" data-testid="meeting-location" />
      </label>
      <div className="flex gap-2">
        <button type="submit" disabled={busy} className="btn-primary text-sm flex-1" data-testid="meeting-submit">
          {busy ? "Saving…" : "Schedule"}
        </button>
        <button type="button" onClick={onClose} className="btn-outline text-sm">Cancel</button>
      </div>
    </form>
  );
}
