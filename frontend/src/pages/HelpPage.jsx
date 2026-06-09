/**
 * Help page — full-page surface for the lightweight support assistant.
 * Reuses the floating HelpAssistant logic via a different layout chrome.
 * Linked from the footer ("Help · Ask the AI") and from the bottom-left
 * floating pill that fires open the widget on every other page.
 */
import React, { useEffect, useRef, useState } from "react";
import { Headphones, Send, Loader2, User, LifeBuoy, MessageCircleQuestion } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const SESSION_KEY = "bright_help_session_id";

export default function HelpPage() {
  const { user } = useAuth();
  const [voice, setVoice] = useState(null);
  const [sessionId, setSessionId] = useState(() => {
    try { return localStorage.getItem(SESSION_KEY) || null; } catch { return null; }
  });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get("/help/voice").then((r) => setVoice(r.data)).catch(() => {});
  }, []);

  // Derive the rendered list (greeting until the user has typed something)
  // to avoid setState-in-effect.
  const rendered = (voice && messages.length === 0)
    ? [{
        role: "assistant", content: voice.greeting,
        follow_up: "How can I help?",
        suggestions: voice.starter_prompts,
        at: new Date().toISOString(),
      }]
    : messages;

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [rendered, busy]);

  const send = async (text) => {
    const t = (text || input).trim();
    if (!t || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: t, at: new Date().toISOString() }]);
    try {
      const { data } = await api.post("/help/chat", { message: t, session_id: sessionId });
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        try { localStorage.setItem(SESSION_KEY, data.session_id); } catch { /* ignore */ }
      }
      setMessages((m) => [...m, {
        role: "assistant", content: data.reply,
        follow_up: data.follow_up,
        escalate_offer: data.escalate_offer,
        at: new Date().toISOString(),
      }]);
    } catch {
      setMessages((m) => [...m, {
        role: "assistant",
        content: "I'm having trouble reaching the server right now. Please email support@birthright.live and we'll respond personally.",
        at: new Date().toISOString(),
      }]);
    } finally {
      setBusy(false);
    }
  };

  const escalate = async () => {
    if (!sessionId) return;
    try {
      const { data } = await api.post("/help/escalate", {
        session_id: sessionId, email: user?.email,
      });
      setMessages((m) => [...m, { role: "assistant", content: data.message, at: new Date().toISOString() }]);
    } catch {
      /* no-op */
    }
  };

  return (
    <div className="container-page py-10 sm:py-14" data-testid="help-page">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <span className="flex items-center justify-center w-10 h-10 rounded-full bg-[#2C4E5A] text-[#FAF8F5]">
            <Headphones size={18} strokeWidth={1.7} />
          </span>
          <div>
            <p className="label !mt-0 text-[#A87A4A]">birthright Help</p>
            <h1 className="font-serif text-2xl sm:text-3xl leading-tight !text-[#1A2424]">
              Ask the AI assistant.
            </h1>
          </div>
        </div>
        <p className="text-sm text-[#5C6B6B] max-w-2xl">
          Trained on Birthright&rsquo;s platform and policies. Most answers come from
          our built-in knowledge base (free). When the question is novel, a small
          AI call is used —{" "}
          {user
            ? "billed to your AI wallet only when the KB can't help."
            : "absorbed by the Foundation for guests."}
          {" "}You can ask for a human at any time.
        </p>

        <div className="mt-8 rounded-2xl border border-[#E5E1D8] bg-[#FAF8F5] overflow-hidden flex flex-col" style={{ minHeight: "60vh" }}>
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-3" data-testid="help-page-messages">
            {rendered.map((m, i) => (
              <PageBubble key={i} m={m} onSuggestion={send} onEscalate={escalate} />
            ))}
            {busy && (
              <div className="flex items-center gap-2 text-xs text-[#5C6B6B] italic">
                <Loader2 size={12} className="animate-spin" /> Birthright Help is typing…
              </div>
            )}
          </div>
          <form
            onSubmit={(e) => { e.preventDefault(); send(); }}
            className="border-t border-[#E5E1D8] bg-white px-3 py-3 flex items-center gap-2"
          >
            <input
              data-testid="help-page-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={user ? "Ask anything…" : "Ask anything (free for guests)…"}
              className="flex-1 bg-[#FAF8F5] border border-[#E5E1D8] rounded-full px-4 py-2.5 text-sm focus:outline-none focus:border-[#476B6B]"
              disabled={busy}
            />
            <button
              type="submit"
              data-testid="help-page-send"
              disabled={busy || !input.trim()}
              className="flex items-center justify-center w-10 h-10 rounded-full bg-[#2C4E5A] text-[#FAF8F5] disabled:opacity-40 hover:bg-[#1F3942] transition"
            >
              <Send size={15} strokeWidth={1.8} />
            </button>
          </form>
        </div>

        <div className="mt-8 grid sm:grid-cols-2 gap-4 text-sm">
          <div className="rounded-lg border border-[#E5E1D8] bg-white p-4">
            <p className="label text-[#476B6B] flex items-center gap-1.5"><LifeBuoy size={11} /> Prefer a human?</p>
            <p className="mt-2 text-[#5C6B6B]">
              Email <a href="mailto:support@birthright.live" className="text-[#2C4E5A] underline">support@birthright.live</a> — typically within one business day.
            </p>
          </div>
          <div className="rounded-lg border border-[#E5E1D8] bg-white p-4">
            <p className="label text-[#476B6B] flex items-center gap-1.5"><MessageCircleQuestion size={11} /> Free for guests</p>
            <p className="mt-2 text-[#5C6B6B]">
              Most answers come from our knowledge base at no cost. When the question
              is novel, a small AI call runs — absorbed by the Foundation for guests,
              billed from your AI wallet for signed-in members.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


function PageBubble({ m, onSuggestion, onEscalate }) {
  const isUser = m.role === "user";
  if (isUser) {
    return (
      <div className="flex items-end justify-end gap-2">
        <div className="max-w-[80%] rounded-2xl rounded-br-md px-4 py-2.5 bg-[#2C4E5A] text-[#FAF8F5] text-sm leading-snug">{m.content}</div>
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-[#E5E1D8] text-[#1A2424]">
          <User size={13} strokeWidth={1.8} />
        </span>
      </div>
    );
  }
  return (
    <div className="space-y-1.5">
      <div className="flex items-start gap-2">
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-[#2C4E5A] text-[#FAF8F5] flex-shrink-0">
          <Headphones size={13} strokeWidth={1.8} />
        </span>
        <div className="max-w-[85%] rounded-2xl rounded-bl-md px-4 py-2.5 bg-white border border-[#E5E1D8] text-sm text-[#1A2424] leading-snug whitespace-pre-wrap">
          <Linkified text={m.content} />
        </div>
      </div>
      {m.follow_up && (
        <p className="ml-9 text-xs italic text-[#5C6B6B]">{m.follow_up}</p>
      )}
      {m.suggestions && m.suggestions.length > 0 && (
        <div className="ml-9 flex flex-wrap gap-1.5 mt-2">
          {m.suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestion(s)}
              className="text-xs px-3 py-1 rounded-full bg-[#F4F1EA] border border-[#E5E1D8] hover:border-[#476B6B] text-[#1A2424]"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      {m.escalate_offer && (
        <button
          onClick={onEscalate}
          className="ml-9 text-[11px] uppercase tracking-wider px-2.5 py-1 rounded-full border border-[#A87A4A] text-[#A87A4A] hover:bg-[#A87A4A]/10"
        >
          Flag for a human
        </button>
      )}
      <p className="ml-9 text-[10px] text-[#9DA8A8]">birthright Help · AI Agent</p>
    </div>
  );
}

function Linkified({ text }) {
  const parts = (text || "").split(/(\bhttps?:\/\/[^\s]+|\b[\w.+-]+@[\w-]+\.[\w.-]+)/g);
  return parts.map((p, i) => {
    if (!p) return null;
    if (p.match(/^https?:\/\//)) {
      return <a key={i} href={p} target="_blank" rel="noreferrer" className="text-[#476B6B] underline hover:text-[#1A2424]">{p}</a>;
    }
    if (p.includes("@") && p.includes(".")) {
      return <a key={i} href={`mailto:${p}`} className="text-[#476B6B] underline hover:text-[#1A2424]">{p}</a>;
    }
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
}
