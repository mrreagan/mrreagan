import React, { useEffect, useState, useRef, useCallback } from "react";
import { Link, useParams, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  MessageSquare, Send, Flag, Archive, Shield, ArrowLeft, CheckCircle2,
  XCircle, Lock, ExternalLink, AlertTriangle,
} from "lucide-react";

import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) {
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ----------- Inbox -----------

export default function Messages() {
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const [params] = useSearchParams();
  const openTo = params.get("to");
  const initial = params.get("initial");
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/dm/threads");
      setThreads(data);
    } catch {
      toast.error("Could not load messages");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  // Auto-open thread if ?to=user_id provided (from "Message" button)
  useEffect(() => {
    if (!openTo || !user) return;
    (async () => {
      try {
        const { data } = await api.post("/dm/threads", {
          recipient_id: openTo,
          initial_message: initial || undefined,
        });
        navigate(`/dashboard/messages/${data.id}`, { replace: true });
      } catch (e) {
        toast.error(e.response?.data?.detail || "Could not open thread");
        navigate("/dashboard/messages", { replace: true });
      }
    })();
  }, [openTo, initial, user, navigate]);

  return (
    <div className="container-page py-12" data-testid="messages-inbox">
      <span className="label">Dashboard · Messages</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <MessageSquare size={28} strokeWidth={1.2} /> Inbox
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Direct messages between you and Birthright partners. To message a partner, look for the
        message icon on their profile or board card.
      </p>
      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-8">Loading…</p>
      ) : threads.length === 0 ? (
        <div className="mt-12 text-center py-12 border border-dashed border-[#E5E1D8] rounded">
          <MessageSquare size={40} strokeWidth={1} className="mx-auto text-[#C9A961]" />
          <p className="mt-4 text-sm text-[#5C6B6B]">No conversations yet.</p>
        </div>
      ) : (
        <ul className="mt-6 card divide-y divide-[#E5E1D8]" data-testid="thread-list">
          {threads.map((t) => (
            <li key={t.id} data-testid={`thread-row-${t.id}`}>
              <Link
                to={`/dashboard/messages/${t.id}`}
                className="block py-4 px-4 hover:bg-[#FAF8F5] transition flex items-center gap-3"
              >
                <Avatar p={t.other_participant} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium truncate">{t.other_participant.name}</p>
                    {t.other_participant.partner_type && (
                      <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">
                        {t.other_participant.partner_type}
                      </span>
                    )}
                    {t.status === "pending" && <StatusBadge tone="warn" label="Pending" />}
                    {t.status === "blocked" && <StatusBadge tone="bad" label="Blocked" />}
                    {t.ombudsman_flagged && <StatusBadge tone="alert" label="Flagged" />}
                  </div>
                  <p className="text-xs text-[#5C6B6B] truncate">{t.last_message_preview || "(no messages yet)"}</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-[#5C6B6B]">{fmtTime(t.last_message_at || t.created_at)}</p>
                  {t.unread_count > 0 && (
                    <span className="inline-block mt-1 bg-[#476B6B] text-white text-[10px] font-medium rounded-full px-2 py-0.5">
                      {t.unread_count}
                    </span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ----------- Thread Detail -----------

export function MessageThread() {
  const { thread_id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [thread, setThread] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [flagOpen, setFlagOpen] = useState(false);
  const [flagReason, setFlagReason] = useState("");
  const bottomRef = useRef(null);
  const wsRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/dm/threads/${thread_id}`);
      setThread(data);
      setMessages(data.messages || []);
      await api.post(`/dm/threads/${thread_id}/read`).catch(() => {});
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not load thread");
      navigate("/dashboard/messages");
    }
  }, [thread_id, navigate]);
  useEffect(() => { load(); }, [load]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // WS for realtime delivery
  useEffect(() => {
    if (!thread_id) return;
    const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
    const wsUrl = backendUrl.replace(/^https?/, backendUrl.startsWith("https") ? "wss" : "ws") + `/api/ws/dm/${thread_id}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "chat" && data.message) {
          setMessages((prev) => {
            if (prev.some((m) => m.id === data.message.id)) return prev;
            return [...prev, data.message];
          });
          // Mark read if not from me
          if (data.message.sender_id !== user?.id) {
            api.post(`/dm/threads/${thread_id}/read`).catch(() => {});
          }
        }
      } catch { /* ignore */ }
    };
    ws.onerror = () => { /* swallow — REST works regardless */ };
    return () => { try { ws.close(); } catch { /* ignore */ } };
  }, [thread_id, user?.id]);

  const send = async () => {
    if (!draft.trim()) return;
    setSending(true);
    try {
      const { data } = await api.post(`/dm/threads/${thread_id}/messages`, { content: draft.trim() });
      setMessages((prev) => prev.some((m) => m.id === data.id) ? prev : [...prev, data]);
      setDraft("");
      // Promote thread to active locally if accepting via reply
      if (thread.status === "pending" && thread.initiator_id !== user.id) {
        setThread({ ...thread, status: "active" });
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not send");
    } finally {
      setSending(false);
    }
  };

  const accept = async () => {
    try {
      await api.post(`/dm/threads/${thread_id}/accept`);
      toast.success("Thread accepted");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  const block = async () => {
    if (!window.confirm("Block this conversation? You won't receive further messages from this sender.")) return;
    try {
      await api.post(`/dm/threads/${thread_id}/block`);
      toast.success("Blocked");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  const archive = async () => {
    try {
      await api.post(`/dm/threads/${thread_id}/archive`);
      toast.success("Archived");
      navigate("/dashboard/messages");
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  const submitFlag = async () => {
    if (flagReason.trim().length < 3) { toast.error("Reason required (≥ 3 chars)"); return; }
    try {
      await api.post(`/dm/threads/${thread_id}/flag`, { reason: flagReason.trim() });
      toast.success("Flagged for ombudsman review");
      setFlagOpen(false); setFlagReason("");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  if (!thread) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</p>;

  const other = thread.other_participant;
  const isPendingForMe = thread.status === "pending" && thread.initiator_id !== user?.id;
  const isPendingForSender = thread.status === "pending" && thread.initiator_id === user?.id;
  const isBlocked = thread.status === "blocked";
  const canSend = thread.status === "active" || isPendingForMe;

  return (
    <div className="container-page py-8" data-testid="message-thread">
      <button onClick={() => navigate("/dashboard/messages")} className="text-xs uppercase tracking-wider text-[#5C6B6B] hover:underline inline-flex items-center gap-1 mb-4" data-testid="back-to-inbox">
        <ArrowLeft size={12} strokeWidth={1.5} /> Inbox
      </button>
      <div className="card overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#E5E1D8] flex items-center gap-3 flex-wrap">
          <Avatar p={other} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium truncate">{other.name}</p>
              {other.partner_type && (
                <Link to={other.partner_slug ? `/partners/${other.partner_slug}` : "#"} className="text-[10px] uppercase tracking-wider text-[#C9A961] hover:underline">
                  {other.partner_type}
                </Link>
              )}
              {thread.status === "pending" && <StatusBadge tone="warn" label="Pending" />}
              {isBlocked && <StatusBadge tone="bad" label="Blocked" />}
              {thread.ombudsman_flagged && <StatusBadge tone="alert" label="Under review" />}
            </div>
            {thread.share_url && (
              <a href={thread.share_url} target="_blank" rel="noreferrer noopener" className="text-[10px] text-[#476B6B] hover:underline inline-flex items-center gap-1 mt-1">
                Started from: {thread.share_url} <ExternalLink size={10} strokeWidth={1.5} />
              </a>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <IconBtn icon={Flag} label="Flag" onClick={() => setFlagOpen(true)} testid="flag-thread" />
            <IconBtn icon={Archive} label="Archive" onClick={archive} testid="archive-thread" />
          </div>
        </div>

        {/* Pending banner for recipient */}
        {isPendingForMe && (
          <div className="px-5 py-3 bg-[#FFFBEF] border-b border-[#E5E1D8] text-sm flex items-center justify-between gap-3 flex-wrap" data-testid="pending-banner">
            <p className="text-[#8B7128] flex items-center gap-2">
              <Shield size={14} strokeWidth={1.5} /> {other.name} would like to start a conversation. Reply to accept, or:
            </p>
            <div className="flex gap-2">
              <button onClick={accept} className="btn-primary text-xs inline-flex items-center gap-1" data-testid="accept-thread">
                <CheckCircle2 size={12} strokeWidth={1.5} /> Accept
              </button>
              <button onClick={block} className="btn-outline text-xs text-[#9E3C3C] border-[#9E3C3C]/40 inline-flex items-center gap-1" data-testid="block-thread">
                <XCircle size={12} strokeWidth={1.5} /> Block
              </button>
            </div>
          </div>
        )}
        {isPendingForSender && (
          <div className="px-5 py-3 bg-[#F2EEE7] border-b border-[#E5E1D8] text-xs text-[#5C6B6B]" data-testid="pending-sender-banner">
            <Lock size={12} strokeWidth={1.5} className="inline mr-1" /> Waiting for {other.name} to accept your message before you can send more.
          </div>
        )}
        {isBlocked && (
          <div className="px-5 py-3 bg-[#F5DDDD] border-b border-[#E5E1D8] text-xs text-[#9E3C3C]" data-testid="blocked-banner">
            <XCircle size={12} strokeWidth={1.5} className="inline mr-1" /> This conversation is blocked.
          </div>
        )}

        {/* Messages */}
        <div className="px-5 py-6 max-h-[60vh] overflow-y-auto bg-[#FAF8F5]" data-testid="messages-list">
          {messages.length === 0 ? (
            <p className="text-center text-xs text-[#5C6B6B]">No messages yet.</p>
          ) : (
            <ul className="space-y-3">
              {messages.map((m) => (
                <li key={m.id} className={`flex ${m.sender_id === user?.id ? "justify-end" : "justify-start"}`} data-testid={`message-${m.id}`}>
                  <div className={`max-w-[75%] px-3 py-2 rounded-2xl ${m.sender_id === user?.id ? "bg-[#476B6B] text-white rounded-br-sm" : "bg-white border border-[#E5E1D8] rounded-bl-sm"}`}>
                    <p className="text-sm whitespace-pre-wrap break-words">{m.content}</p>
                    {m.share_url && (
                      <a href={m.share_url} target="_blank" rel="noreferrer noopener" className={`block mt-1 text-[10px] underline ${m.sender_id === user?.id ? "text-white/80" : "text-[#476B6B]"}`}>
                        {m.share_url}
                      </a>
                    )}
                    <p className={`text-[10px] mt-1 ${m.sender_id === user?.id ? "text-white/70" : "text-[#5C6B6B]"}`}>{fmtTime(m.created_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        {canSend && (
          <div className="px-5 py-3 border-t border-[#E5E1D8] flex gap-2" data-testid="composer">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Write a message…"
              rows={2}
              className="input-field text-sm flex-1 resize-none"
              data-testid="composer-input"
              disabled={sending}
            />
            <button onClick={send} disabled={sending || !draft.trim()} className="btn-primary text-xs px-4 inline-flex items-center gap-1" data-testid="composer-send">
              <Send size={12} strokeWidth={1.5} /> {sending ? "…" : "Send"}
            </button>
          </div>
        )}
      </div>

      {flagOpen && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="flag-modal">
          <div className="bg-white rounded shadow-xl max-w-md w-full p-6">
            <h3 className="font-serif text-xl inline-flex items-center gap-2">
              <AlertTriangle size={18} strokeWidth={1.5} className="text-[#C9A961]" /> Flag for ombudsman review
            </h3>
            <p className="text-sm text-[#5C6B6B] mt-2">
              The Birthright ombudsman will be able to read this conversation for the purpose of review.
              Use this for safety concerns, abuse, or boundary violations.
            </p>
            <textarea
              value={flagReason}
              onChange={(e) => setFlagReason(e.target.value)}
              className="input-field text-sm w-full mt-4"
              rows={3}
              placeholder="Briefly describe the concern…"
              data-testid="flag-reason-input"
            />
            <div className="flex gap-2 mt-4">
              <button onClick={submitFlag} className="btn-primary text-xs" data-testid="flag-submit">Submit flag</button>
              <button onClick={() => setFlagOpen(false)} className="btn-outline text-xs">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------- Shared bits -----------

function Avatar({ p }) {
  if (p?.avatar_url) {
    return <img src={p.avatar_url} alt={p.name} className="w-10 h-10 rounded-full object-cover bg-[#E5E1D8]" />;
  }
  const initials = (p?.name || "?").split(" ").map((s) => s[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
  return (
    <div className="w-10 h-10 rounded-full bg-[#C9A961] text-white flex items-center justify-center text-xs font-medium">
      {initials || "?"}
    </div>
  );
}

function StatusBadge({ tone, label }) {
  const cls = tone === "warn"  ? "bg-[#FDF1E8] text-[#B86A5C]"
            : tone === "bad"   ? "bg-[#F5DDDD] text-[#9E3C3C]"
            : tone === "alert" ? "bg-[#FFF8E1] text-[#8B7128]"
                               : "bg-[#E8F0EA] text-[#2E5C46]";
  return <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${cls}`}>{label}</span>;
}

function IconBtn({ icon: Icon, label, onClick, testid }) {
  return (
    <button
      onClick={onClick}
      className="text-[10px] uppercase tracking-wider text-[#5C6B6B] hover:text-[#1A2424] flex flex-col items-center px-2 py-1 rounded hover:bg-[#FAF8F5]"
      data-testid={testid}
      title={label}
    >
      <Icon size={14} strokeWidth={1.5} />
      <span className="text-[8px] mt-0.5">{label}</span>
    </button>
  );
}
