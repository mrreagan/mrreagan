import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import useChatSocket from "../../hooks/useChatSocket";

import ConnectionPill from "./chat/ConnectionPill";
import ParticipantsSidebar from "./chat/ParticipantsSidebar";
import MessagesList from "./chat/MessagesList";
import TypingIndicator from "./chat/TypingIndicator";

const POLL_INTERVAL_MS = 4000;
const TYPING_DEBOUNCE_MS = 800;
const TYPING_CLEAR_MS = 3000;

function viewMatchesChatMessage(m, viewRecipientId, currentUserId) {
  if (!viewRecipientId) return !m.recipient_id;  // group view: only undirected msgs
  // DM view between current user and viewRecipientId — accept both directions
  return (
    (m.recipient_id === viewRecipientId && m.sender_id === currentUserId) ||
    (m.sender_id === viewRecipientId && m.recipient_id === currentUserId)
  );
}

function viewMatchesTyping(data, viewRecipientId, currentUserId) {
  if (!viewRecipientId) return !data.recipient_id;
  return data.recipient_id === currentUserId || data.recipient_id === viewRecipientId;
}

export default function ChatTab({ workshop, user }) {
  const [messages, setMessages] = useState([]);
  const [recipientId, setRecipientId] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [presence, setPresence] = useState([]);
  const [typingUsers, setTypingUsers] = useState({});
  const [text, setText] = useState("");
  const scrollRef = useRef(null);
  const lastTypingSentRef = useRef(0);
  const lastPollRef = useRef(null);
  const recipientIdRef = useRef(recipientId);
  recipientIdRef.current = recipientId;

  const handleWsMessage = useCallback((data) => {
    if (data.type === "chat" && data.message) {
      const m = data.message;
      if (!viewMatchesChatMessage(m, recipientIdRef.current, user.id)) return;
      setMessages((prev) => prev.some((x) => x.id === m.id) ? prev : [...prev, m]);
      return;
    }
    if (data.type === "typing") {
      if (data.user_id === user.id) return;  // ignore own typing echo
      if (!viewMatchesTyping(data, recipientIdRef.current, user.id)) return;
      setTypingUsers((prev) => {
        const next = { ...prev };
        if (data.is_typing) next[data.user_id] = { name: data.user_name, expires_at: Date.now() + TYPING_CLEAR_MS };
        else delete next[data.user_id];
        return next;
      });
      return;
    }
    if (data.type === "presence") {
      setPresence(data.users || []);
    }
  }, [user.id]);

  const { status, send: wsSend } = useChatSocket({ workshopId: workshop.id, onMessage: handleWsMessage });

  // Sweep stale typing entries each second.
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

  // Polling fallback when WS surrenders to 'fallback'.
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

  // Load initial history + participants whenever workshop or DM target changes.
  useEffect(() => {
    setMessages([]);
    setTypingUsers({});
    lastPollRef.current = null;
    api.get(`/chat/participants?workshop_id=${workshop.id}`)
      .then((r) => setParticipants(r.data))
      .catch((err) => console.error("Chat participants load failed:", err?.message || err));
    const params = new URLSearchParams({ workshop_id: workshop.id });
    if (recipientId) params.append("recipient_id", recipientId);
    api.get(`/chat?${params}`)
      .then((r) => {
        setMessages(r.data);
        if (r.data.length) lastPollRef.current = r.data[r.data.length - 1].created_at;
      })
      .catch((err) => console.error("Chat history load failed:", err?.message || err));
  }, [workshop.id, recipientId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const sendChat = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content) return;
    setText("");
    const wsOk = wsSend({ type: "chat", content, recipient_id: recipientId });
    if (wsOk) return;
    try {
      const { data } = await api.post("/chat", { workshop_id: workshop.id, content, recipient_id: recipientId });
      setMessages((prev) => [...prev, data]);
    } catch (err) {
      console.error("Chat REST send failed:", err?.message || err);
      toast.error("Could not send");
      setText(content);
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
      <div className="lg:col-span-3 card p-5 flex flex-col" style={{ minHeight: "500px" }} data-testid="chat-pane">
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
