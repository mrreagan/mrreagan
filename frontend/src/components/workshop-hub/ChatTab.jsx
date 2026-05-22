import React, { useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";

function ParticipantsSidebar({ participants, recipientId, onSelect }) {
  return (
    <div className="card p-4 lg:max-h-[600px] lg:overflow-y-auto" data-testid="chat-participants">
      <span className="label">Conversations</span>
      <button
        onClick={() => onSelect(null)}
        className={`block w-full text-left mt-3 px-3 py-2 rounded-lg text-sm ${
          !recipientId ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"
        }`}
        data-testid="chat-group"
      >
        # Group chat
      </button>
      <div className="mt-2 space-y-1">
        {participants.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`block w-full text-left px-3 py-2 rounded-lg text-sm ${
              recipientId === p.id ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"
            }`}
            data-testid={`chat-user-${p.id}`}
          >
            {p.name}
            {p.role === "facilitator" && (
              <span className="text-[10px] uppercase tracking-wider ml-1 opacity-70">facilitator</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message, isMine }) {
  return (
    <div className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${isMine ? "bg-[#476B6B] text-white" : "bg-[#FAF8F5] text-[#1A2424]"}`}>
        {!isMine && <p className="text-[10px] uppercase tracking-wider opacity-60 mb-0.5">{message.sender_name}</p>}
        <p className="text-sm">{message.content}</p>
      </div>
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

function MessageInput({ value, onChange, onSend }) {
  return (
    <form onSubmit={onSend} className="mt-4 flex gap-2">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type a message"
        className="input-field flex-1"
        data-testid="chat-input"
      />
      <button type="submit" className="btn-primary" data-testid="chat-send">
        <Send size={14} strokeWidth={1.5} />
      </button>
    </form>
  );
}

export default function ChatTab({ workshop, user }) {
  const [messages, setMessages] = useState([]);
  const [recipientId, setRecipientId] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [text, setText] = useState("");
  const lastFetchRef = useRef(null);
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    const params = new URLSearchParams({ workshop_id: workshop.id });
    if (recipientId) params.append("recipient_id", recipientId);
    if (lastFetchRef.current) params.append("since", lastFetchRef.current);
    try {
      const { data } = await api.get(`/chat?${params}`);
      if (data.length) {
        setMessages((prev) => {
          const merged = [...prev, ...data];
          lastFetchRef.current = merged[merged.length - 1].created_at;
          return merged;
        });
      }
    } catch (err) {
      console.error("Chat load failed:", err?.message || err);
    }
  }, [workshop.id, recipientId]);

  useEffect(() => {
    setMessages([]);
    lastFetchRef.current = null;
    api.get(`/chat/participants?workshop_id=${workshop.id}`).then((r) => setParticipants(r.data));
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load, workshop.id]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      await api.post("/chat", { workshop_id: workshop.id, content: text, recipient_id: recipientId });
      setText("");
      load();
    } catch {
      toast.error("Could not send");
    }
  };

  const headerLabel = recipientId
    ? participants.find((p) => p.id === recipientId)?.name
    : "Group chat";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6" data-testid="tab-chat">
      <ParticipantsSidebar participants={participants} recipientId={recipientId} onSelect={setRecipientId} />
      <div className="lg:col-span-3 card p-5 flex flex-col" style={{ minHeight: "500px" }}>
        <span className="label">{headerLabel}</span>
        <MessagesList messages={messages} currentUserId={user?.id} scrollRef={scrollRef} />
        <MessageInput value={text} onChange={setText} onSend={send} />
      </div>
    </div>
  );
}
