/**
 * HelpAssistant — lightweight support chat in the YesChef style.
 *
 * Design goals:
 *   - Bottom-LEFT floating "Need help?" pill on every page.
 *   - Bottom-of-footer tab link (added in Layout.jsx).
 *   - Token-efficient: backend KB-deflects most questions for free; only
 *     novel questions hit Claude Haiku 4.5 and only logged-in members
 *     are billed (via their AI wallet).
 *
 * Session persistence: session_id lives in localStorage so a member's
 * conversation continues across tabs/refreshes.
 */
import React, { useEffect, useRef, useState } from "react";
import { LifeBuoy, X, Send, User, Loader2, Headphones } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const SESSION_KEY = "bright_help_session_id";
const OPEN_KEY = "bright_help_open";

function loadSessionId() {
  try { return localStorage.getItem(SESSION_KEY) || null; } catch { return null; }
}
function saveSessionId(id) {
  try { localStorage.setItem(SESSION_KEY, id); } catch { /* ignore */ }
}

// Display-only timestamp ("5m" / "Just now") to match the YesChef style.
function relTime(iso) {
  if (!iso) return "Just now";
  const dt = new Date(iso);
  const mins = Math.floor((Date.now() - dt.getTime()) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return dt.toLocaleDateString();
}

export default function HelpAssistant() {
  const { user } = useAuth();
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(OPEN_KEY) === "1"; } catch { return false; }
  });
  const [voice, setVoice] = useState(null);
  const [sessionId, setSessionId] = useState(loadSessionId);
  const [messages, setMessages] = useState([]); // {role, content, at, follow_up?, escalate_offer?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    try { localStorage.setItem(OPEN_KEY, open ? "1" : "0"); } catch { /* ignore */ }
    if (open) setTimeout(() => inputRef.current?.focus(), 120);
  }, [open]);

  // Fetch voice once on mount.
  useEffect(() => {
    if (!voice) {
      api.get("/help/voice").then((r) => setVoice(r.data)).catch(() => {});
    }
  }, [voice]);

  // Derive the rendered message list: prepend the greeting until the user
  // actually types something. This avoids setState-in-effect (React 19).
  const renderedMessages = (voice && messages.length === 0)
    ? [{
        role: "assistant",
        content: voice.greeting,
        at: new Date().toISOString(),
        follow_up: "How can I help?",
        suggestions: voice.starter_prompts || [],
      }]
    : messages;

  // Auto-scroll on every new message.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [renderedMessages, busy]);

  const send = async (text) => {
    const t = (text || input).trim();
    if (!t || busy) return;
    setInput("");
    setBusy(true);
    const userTurn = { role: "user", content: t, at: new Date().toISOString() };
    setMessages((m) => [...m, userTurn]);
    try {
      const { data } = await api.post("/help/chat", {
        message: t,
        session_id: sessionId,
      });
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        saveSessionId(data.session_id);
      }
      setMessages((m) => [...m, {
        role: "assistant",
        content: data.reply,
        follow_up: data.follow_up,
        escalate_offer: data.escalate_offer,
        cost_usd: data.cost_usd,
        source: data.source,
        at: new Date().toISOString(),
      }]);
    } catch (e) {
      setMessages((m) => [...m, {
        role: "assistant",
        content: "I'm having trouble reaching the server right now — please email support@birthright.live and we'll respond personally.",
        at: new Date().toISOString(),
        escalate_offer: true,
      }]);
    } finally {
      setBusy(false);
    }
  };

  const escalate = async () => {
    if (!sessionId) return;
    try {
      const { data } = await api.post("/help/escalate", {
        session_id: sessionId,
        email: user?.email,
      });
      setMessages((m) => [...m, {
        role: "assistant",
        content: data.message,
        at: new Date().toISOString(),
      }]);
    } catch (_) {
      setMessages((m) => [...m, {
        role: "assistant",
        content: "Email support@birthright.live directly — a human at the Foundation will respond within one business day.",
        at: new Date().toISOString(),
      }]);
    }
  };

  return (
    <>
      {/* Floating quick-link pill — bottom-LEFT. */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          data-testid="help-open-btn"
          className="fixed bottom-6 left-6 z-40 flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#FAF8F5] text-[#1A2424] border border-[#E5E1D8] shadow-[0_6px_24px_rgba(26,36,36,0.08)] hover:bg-[#F4F1EA] hover:shadow-[0_8px_32px_rgba(26,36,36,0.12)] transition"
          aria-label="Open help chat"
        >
          <LifeBuoy size={16} strokeWidth={1.6} className="text-[#476B6B]" />
          <span className="text-sm font-medium">Need help?</span>
        </button>
      )}

      {open && (
        <div
          data-testid="help-panel"
          className="fixed bottom-6 left-6 right-6 sm:right-auto sm:w-[400px] z-40 flex flex-col rounded-2xl bg-[#FAF8F5] border border-[#E5E1D8] shadow-[0_24px_80px_rgba(15,36,36,0.2)] overflow-hidden"
          style={{ maxHeight: "min(640px, 80vh)" }}
        >
          {/* Header */}
          <header className="flex items-center justify-between gap-2 px-5 py-3.5 border-b border-[#E5E1D8] bg-white">
            <div className="flex items-center gap-2.5">
              <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[#2C4E5A] text-[#FAF8F5]">
                <Headphones size={14} strokeWidth={1.8} />
              </span>
              <div className="leading-tight">
                <p className="font-serif text-sm">
                  {voice?.agent_name || "Birthright Help"}
                </p>
                <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                  {voice?.agent_label || "AI Agent"} · Online
                </p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              data-testid="help-close-btn"
              className="p-1.5 rounded-full text-[#5C6B6B] hover:bg-[#F4F1EA]"
              aria-label="Close help chat"
            >
              <X size={16} strokeWidth={1.7} />
            </button>
          </header>

          {/* Message list */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
            data-testid="help-messages"
          >
            {renderedMessages.map((m, i) => (
              <HelpBubble
                key={i}
                m={m}
                onSuggestion={send}
                onEscalate={escalate}
                userLabel={user?.name || user?.email?.split("@")[0] || "You"}
              />
            ))}
            {busy && (
              <div className="flex items-center gap-2 text-xs text-[#5C6B6B] italic px-1" data-testid="help-typing">
                <Loader2 size={12} className="animate-spin" /> Birthright Help is typing…
              </div>
            )}
          </div>

          {/* Composer */}
          <form
            className="border-t border-[#E5E1D8] bg-white px-3 py-2.5 flex items-center gap-2"
            onSubmit={(e) => { e.preventDefault(); send(); }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={user ? "Ask anything…" : "Ask anything (free for guests)…"}
              data-testid="help-input"
              className="flex-1 bg-[#FAF8F5] border border-[#E5E1D8] rounded-full px-4 py-2 text-sm text-[#1A2424] placeholder:text-[#9DA8A8] focus:outline-none focus:border-[#476B6B]"
              disabled={busy}
            />
            <button
              type="submit"
              data-testid="help-send"
              disabled={busy || !input.trim()}
              className="flex items-center justify-center w-9 h-9 rounded-full bg-[#2C4E5A] text-[#FAF8F5] disabled:opacity-40 hover:bg-[#1F3942] transition"
              aria-label="Send"
            >
              <Send size={14} strokeWidth={1.8} />
            </button>
          </form>
          <p className="text-[10px] text-[#9DA8A8] text-center pb-2 px-3">
            {user ? "AI responses bill from your wallet only when the KB can't answer." : "Free to guests · Foundation absorbs the cost."}
          </p>
        </div>
      )}
    </>
  );
}


function HelpBubble({ m, onSuggestion, onEscalate, userLabel }) {
  const isUser = m.role === "user";
  if (isUser) {
    return (
      <div className="flex items-end justify-end gap-2" data-testid="help-bubble-user">
        <div className="max-w-[80%] rounded-2xl rounded-br-md px-3.5 py-2 bg-[#2C4E5A] text-[#FAF8F5] text-sm leading-snug">
          {m.content}
        </div>
        <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#E5E1D8] text-[#1A2424] text-[10px]">
          <User size={11} strokeWidth={1.8} />
        </span>
      </div>
    );
  }
  return (
    <div className="space-y-1.5" data-testid="help-bubble-assistant">
      <div className="flex items-start gap-2">
        <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#2C4E5A] text-[#FAF8F5] flex-shrink-0">
          <Headphones size={11} strokeWidth={1.8} />
        </span>
        <div className="max-w-[85%] rounded-2xl rounded-bl-md px-3.5 py-2 bg-white border border-[#E5E1D8] text-sm text-[#1A2424] leading-snug whitespace-pre-wrap">
          <LinkifiedText text={m.content} />
        </div>
      </div>
      {m.follow_up && (
        <div className="flex items-start gap-2 ml-8">
          <div className="text-xs italic text-[#5C6B6B]">{m.follow_up}</div>
        </div>
      )}
      {m.suggestions && m.suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 ml-8 mt-2" data-testid="help-suggestions">
          {m.suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestion(s)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-[#F4F1EA] border border-[#E5E1D8] hover:border-[#476B6B] text-[#1A2424]"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      {m.escalate_offer && (
        <div className="ml-8 mt-1">
          <button
            onClick={onEscalate}
            data-testid="help-escalate"
            className="text-[11px] uppercase tracking-wider px-2.5 py-1 rounded-full border border-[#A87A4A] text-[#A87A4A] hover:bg-[#A87A4A]/10"
          >
            Flag for a human
          </button>
        </div>
      )}
      <p className="text-[10px] text-[#9DA8A8] ml-8 mt-0.5">
        {voice_label(m)} · {relTime(m.at)}
      </p>
    </div>
  );
}

function voice_label(m) {
  // Match the YesChef format: "YesChef Support • AI Agent • 5m"
  return "Birthright Help · AI Agent";
}

// Simple URL detection — auto-link http(s) URLs and email-like tokens.
function LinkifiedText({ text }) {
  const parts = (text || "").split(/(\bhttps?:\/\/[^\s]+|\b[\w.+-]+@[\w-]+\.[\w.-]+)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (!p) return null;
        if (p.match(/^https?:\/\//)) {
          return (
            <a key={i} href={p} target="_blank" rel="noreferrer" className="text-[#476B6B] underline hover:text-[#1A2424]">
              {p}
            </a>
          );
        }
        if (p.includes("@") && p.includes(".")) {
          return (
            <a key={i} href={`mailto:${p}`} className="text-[#476B6B] underline hover:text-[#1A2424]">
              {p}
            </a>
          );
        }
        return <React.Fragment key={i}>{p}</React.Fragment>;
      })}
    </>
  );
}
