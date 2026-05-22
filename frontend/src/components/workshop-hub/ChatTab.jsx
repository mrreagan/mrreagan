import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Send, Wifi, WifiOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import useChatSocket from "../../hooks/useChatSocket";

const POLL_INTERVAL_MS = 4000;
const TYPING_DEBOUNCE_MS = 800;
const TYPING_CLEAR_MS = 3000;

function ConnectionPill({ status }) {
  const cfg = {
    connecting:   { label: "Connecting…", cls: "bg-[#FAF8F5] text-[#5C6B6B]", icon: Loader2, spin: true },
    connected:    { label: "Live",        cls: "bg-[#2E5C46]/10 text-[#2E5C46]", icon: Wifi },
    reconnecting: { label: "Reconnecting…", cls: "bg-[#C9A961]/15 text-[#C9A961]", icon: Loader2, spin: true },
    fallback:     { label: "Slow mode",   cls: "bg-[#C9A961]/15 text-[#C9A961]", icon: WifiOff },
    offline:      { label: "Offline",     cls: "bg-[#B86A5C]/10 text-[#B86A5C]", icon: WifiOff },
  }[status] || { label: status, cls: "bg-[#FAF8F5]" };
  const Icon = cfg.icon || Wifi;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${cfg.cls}`} data-testid={`chat-status-${status}`}>
      <Icon size={10} strokeWidth={2} className={cfg.spin ? "animate-spin" : ""} />
      {cfg.label}
    </span>
  );
}

function ParticipantsSidebar({ participants, recipientId, onSelect, presenceIds }) {
  return (
    <div className="card p-4 lg:max-h-[600px] lg:overflow-y-auto" data-testid="chat-participants">
      <span className="label">Conversations</span>
      <button
        onClick={() => onSelect(null)}
        className={`block w-full text-left mt-3 px-3 py-2 rounded-lg text-sm ${!recipientId ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"}`}
        data-testid="chat-group"
      >
        # Group chat
      </button>
      <div className="mt-2 space-y-1">
        {participants.map((p) => {
          const online = presenceIds.has(p.id);
          return (
            <button
              key={p.id}
              onClick={() => onSelect(p.id)}
              className={`flex items-center justify-between w-full text-left px-3 py-2 rounded-lg text-sm ${recipientId === p.id ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"}`}
              data-testid={`chat-user-${p.id}`}
            >
              <span>
                {p.name}
                {p.role === "facilitator" && <span className="text-[10px] uppercase tracking-wider ml-1 opacity-70">facilitator</span>}
              </span>
              {online && <span className={`w-1.5 h-1.5 rounded-full ${recipientId === p.id ? "bg-white" : "bg-[#2E5C46]"}`} title="online" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MessageBubble({ message, isMine }) {
  return (
    <div className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${isMine ? "bg-[#476B6B] text-white" : "bg-[#FAF8F5] text-[#1A2424]"}`}>
        {!isMine && <p className="text-[10px] uppercase tracking-wider opacity-60 mb-0.5">{message.sender_name}</p>}
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
      </div>
    </div>
  );
}

function TypingIndicator({ names }) {
  if (!names.length) return null;
  const label =
    names.length === 1 ? `${names[0]} is typing…`
    : names.length === 2 ? `${names[0]} and ${names[1]} are typing…`
    : `${names.length} people are typing…`;
  return (
    <div className="flex items-center gap-2 text-xs text-[#5C6B6B] italic px-1" data-testid="chat-typing">
      <span className="inline-flex gap-0.5">
        <span className="w-1 h-1 rounded-full bg-[#5C6B6B] animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-1 h-1 rounded-full bg-[#5C6B6B] animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-1 h-1 rounded-full bg-[#5C6B6B] animate-bounce" style={{ animationDelay: "300ms" }} />
      </span>
      {label}
    </div>
  );
}

function MessagesList({ messages, currentUserId, scrollRef }) {
  return (
    <div ref={scrollRef} className="flex-1 mt-4 overflow-y-auto space-y-3 max-h-[420px] pr-2" data-testid="chat-messages">
      {messages.length === 0 && <p className="text-sm text-[#5C6B6B] text-center py-10">No messages yet.</p>}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} isMine={m.sender_id === currentUserId} />
      ))}
    </div>
  );
}

export default function ChatTab({ workshop, user }) {
  const [messages, setMessages] = useState([]);
  const [recipientId, setRecipientId] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [presence, setPresence] = useState([]); // [{id,name,role}]
  const [typingUsers, setTypingUsers] = useState({}); // user_id → {name, expires_at, recipient_id}
  const [text, setText] = useState("");
  const scrollRef = useRef(null);
  const lastTypingSentRef = useRef(0);
  const lastPollRef = useRef(null);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const recipientIdRef = useRef(recipientId);
  recipientIdRef.current = recipientId;

  const handleWsMessage = useCallback((data) => {
    if (data.type === "chat" && data.message) {
      const m = data.message;
      const rid = recipientIdRef.current;
      // For DMs we only show messages between current user and selected partner.
      // For group view we only show messages with recipient_id === null.
      const matchesView = rid
        ? (m.recipient_id === rid && m.sender_id === user.id) || (m.sender_id === rid && m.recipient_id === user.id)
        : !m.recipient_id;
      if (!matchesView) return;
      setMessages((prev) => prev.some((x) => x.id === m.id) ? prev : [...prev, m]);
    } else if (data.type === "typing") {
      if (data.user_id === user.id) return; // ignore own typing echo
      const matchesView = recipientIdRef.current
        ? data.recipient_id === user.id || data.recipient_id === recipientIdRef.current
        : !data.recipient_id;
      if (!matchesView) return;
      setTypingUsers((prev) => {
        const next = { ...prev };
        if (data.is_typing) {
          next[data.user_id] = { name: data.user_name, expires_at: Date.now() + TYPING_CLEAR_MS };
        } else {
          delete next[data.user_id];
        }
        return next;
      });
    } else if (data.type === "presence") {
      setPresence(data.users || []);
    }
  }, [user.id]);

  const { status, send: wsSend } = useChatSocket({ workshopId: workshop.id, onMessage: handleWsMessage });

  // Sweep stale typing entries
  useEffect(() => {
    const t = setInterval(() => {
      setTypingUsers((prev) => {
        const now = Date.now();
        const next = {};
        let changed = false;
        for (const [k, v] of Object.entries(prev)) {
          if (v.expires_at > now) next[k] = v;
          else changed = true;
        }
        return changed ? next : prev;
      });
    }, 1000);
    return () => clearInterval(t);
  }, []);

  // Polling fallback when WS gives up
  useEffect(() => {
    if (status !== "fallback") return undefined;
    let cancelled = false;
    const poll = async () => {
      const params = new URLSearchParams({ workshop_id: workshop.id });
      if (recipientId) params.append("recipient_id", recipientId);
      if (lastPollRef.current) params.append("since", lastPollRef.current);
      try {
        const { data } = await api.get(`/chat?${params}`);
        if (cancelled) return;
        if (data.length) {
          setMessages((prev) => {
            const merged = [...prev, ...data.filter((d) => !prev.some((x) => x.id === d.id))];
            if (merged.length) lastPollRef.current = merged[merged.length - 1].created_at;
            return merged;
          });
        }
      } catch (err) {
        console.error("Chat poll failed:", err?.message || err);
      }
    };
    const t = setInterval(poll, POLL_INTERVAL_MS);
    poll();
    return () => { cancelled = true; clearInterval(t); };
  }, [status, workshop.id, recipientId]);

  // Load initial history + participants whenever workshop or DM target changes
  useEffect(() => {
    setMessages([]);
    setTypingUsers({});
    lastPollRef.current = null;
    api.get(`/chat/participants?workshop_id=${workshop.id}`).then((r) => setParticipants(r.data));
    const params = new URLSearchParams({ workshop_id: workshop.id });
    if (recipientId) params.append("recipient_id", recipientId);
    api.get(`/chat?${params}`).then((r) => {
      setMessages(r.data);
      if (r.data.length) lastPollRef.current = r.data[r.data.length - 1].created_at;
    }).catch((err) => console.error("Chat history load failed:", err?.message || err));
  }, [workshop.id, recipientId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const sendChat = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content) return;
    setText("");
    // Try WS first, fall back to REST
    const wsOk = wsSend({ type: "chat", content, recipient_id: recipientId });
    if (!wsOk) {
      try {
        const { data } = await api.post("/chat", { workshop_id: workshop.id, content, recipient_id: recipientId });
        setMessages((prev) => [...prev, data]);
      } catch {
        toast.error("Could not send");
        setText(content);
      }
    }
  };

  const onType = (e) => {
    setText(e.target.value);
    if (status !== "connected") return;
    const now = Date.now();
    if (now - lastTypingSentRef.current >= TYPING_DEBOUNCE_MS) {
      lastTypingSentRef.current = now;
      wsSend({ type: "typing", is_typing: true, recipient_id: recipientId });
    }
  };

  const presenceIds = useMemo(() => new Set(presence.map((p) => p.id)), [presence]);
  const typingNames = useMemo(() => Object.values(typingUsers).map((t) => t.name), [typingUsers]);

  const headerLabel = recipientId
    ? participants.find((p) => p.id === recipientId)?.name
    : "Group chat";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6" data-testid="tab-chat">
      <ParticipantsSidebar participants={participants} recipientId={recipientId} onSelect={setRecipientId} presenceIds={presenceIds} />
      <div className="lg:col-span-3 card p-5 flex flex-col" style={{ minHeight: "500px" }}>
        <div className="flex items-center justify-between">
          <span className="label">{headerLabel}</span>
          <ConnectionPill status={status} />
        </div>
        <MessagesList messages={messages} currentUserId={user?.id} scrollRef={scrollRef} />
        <TypingIndicator names={typingNames} />
        <form onSubmit={sendChat} className="mt-3 flex gap-2">
          <input
            value={text}
            onChange={onType}
            placeholder={status === "fallback" ? "Type a message (slow mode)" : "Type a message"}
            className="input-field flex-1"
            data-testid="chat-input"
            maxLength={4000}
          />
          <button type="submit" className="btn-primary" data-testid="chat-send">
            <Send size={14} strokeWidth={1.5} />
          </button>
        </form>
      </div>
    </div>
  );
}
