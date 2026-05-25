/**
 * AssistantWidget — site-wide AI Concierge for Birthright (Phase 6B.6).
 *
 * Floating bottom-right button on every page. Press `/` (when not in an input)
 * to toggle. Opens a slide-in panel with conversational chat backed by Claude
 * Sonnet 4.5 via the /api/assistant endpoints.
 *
 * Agentic actions:
 *   - tier "auto" actions execute immediately (navigate, prefill, scroll,
 *     open_modal, search_*, lookup_*).
 *   - tier "confirm" actions render a confirmation card the user must accept
 *     before anything happens.
 *
 * Backend-executed actions return their result, which we surface as an
 * inline system message. Frontend-executed actions return a "directive" that
 * we run locally (e.g., navigate via react-router).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Send, X, ChevronDown, AlertCircle, CheckCircle2, Loader2, History, Wallet } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const SESSION_KEY = "bright_assistant_session_id";
const OPEN_KEY = "bright_assistant_open";

function loadSessionId() {
  try { return localStorage.getItem(SESSION_KEY) || null; } catch { return null; }
}
function saveSessionId(id) {
  try { localStorage.setItem(SESSION_KEY, id); } catch { /* ignore */ }
}

function formatError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((x) => x?.msg || x?.message || JSON.stringify(x)).join("; ");
  }
  if (d && typeof d === "object") return JSON.stringify(d);
  return e?.message || "Something went wrong.";
}

export default function AssistantWidget() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(OPEN_KEY) === "1"; } catch { return false; }
  });
  const [sessionId, setSessionId] = useState(loadSessionId);
  const [messages, setMessages] = useState([]); // {id, role, content, actions?, kind?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Persist open state
  useEffect(() => {
    try { localStorage.setItem(OPEN_KEY, open ? "1" : "0"); } catch { /* ignore */ }
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  // Keyboard shortcut: `/` toggles (when not typing in another input,
  // OR when the assistant input itself is empty — lets mobile users escape).
  useEffect(() => {
    const onKey = (e) => {
      const target = e.target;
      const isAssistantInput = target && target.dataset && target.dataset.testid === "assistant-input";
      const inOtherField = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) && !isAssistantInput;
      const assistantInputIsEmpty = isAssistantInput && !target.value;
      if (e.key === "/" && !inOtherField && (!isAssistantInput || assistantInputIsEmpty) && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  const pageContext = useMemo(() => ({
    path: location.pathname,
    title: document.title || "",
    notes: "",
  }), [location.pathname]);

  // --- Action executor ----------------------------------------------------
  const runDirective = useCallback((directive) => {
    if (!directive || !directive.type) return false;
    switch (directive.type) {
      case "navigate": {
        const p = directive.params?.path;
        if (typeof p === "string" && p.startsWith("/")) {
          navigate(p);
          // Auto-close so the user actually SEES the page they asked for.
          // Otherwise the fullscreen mobile panel hides the new page.
          setOpen(false);
          toast.success(`Navigated to ${p}`);
          return true;
        }
        return false;
      }
      case "scroll_to": {
        const id = directive.params?.element_id;
        if (id) {
          const el = document.getElementById(id);
          if (el) { el.scrollIntoView({ behavior: "smooth", block: "start" }); return true; }
        }
        return false;
      }
      case "prefill_form": {
        const { form_id, values } = directive.params || {};
        if (!form_id || !values) return false;
        const form = document.getElementById(form_id) || document.querySelector(`[data-form-id="${form_id}"]`);
        if (!form) return false;
        let count = 0;
        for (const [k, v] of Object.entries(values)) {
          const el = form.querySelector(`[name="${k}"], [data-testid="${k}"]`);
          if (el) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
            try { setter?.call(el, v); } catch { el.value = v; }
            el.dispatchEvent(new Event("input", { bubbles: true }));
            count++;
          }
        }
        return count > 0;
      }
      case "open_modal": {
        // Modals open in many ways; we surface this as a hint instead of trying to dispatch.
        return false;
      }
      case "add_to_cart": {
        // Defer to global event the cart context listens to (graceful no-op if absent).
        window.dispatchEvent(new CustomEvent("bright:add-to-cart", { detail: directive.params }));
        return true;
      }
      case "register_for_workshop": {
        const wid = directive.params?.workshop_id;
        if (wid) { navigate(`/workshops/${wid}`); setOpen(false); toast.success(`Navigated to /workshops/${wid}`); return true; }
        return false;
      }
      default:
        return false;
    }
  }, [navigate]);

  const execAction = useCallback(async (action, overrideSessionId) => {
    setBusy(true);
    try {
      const res = await api.post("/assistant/execute", {
        session_id: overrideSessionId || sessionId || "anonymous",
        action_id: action.id,
        action_type: action.type,
        params: action.params || {},
      });
      const data = res.data || {};
      if (!data.ok) {
        setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "error", content: data.error || "Action failed." }]);
        toast.error(data.error || "Action failed");
        return;
      }
      if (data.directive) {
        const ran = runDirective(data.directive);
        if (!ran) {
          setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "info", content: `I couldn't run "${action.label}" automatically here, but you can do it manually.` }]);
        } else {
          setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "ok", content: `✓ ${action.label}` }]);
        }
      } else {
        // backend-executed: show a compact result line
        let summary = `✓ ${action.label}`;
        if (Array.isArray(data.result)) summary += ` — ${data.result.length} result(s)`;
        setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "ok", content: summary, payload: data.result }]);
      }
      // Mark action as accepted locally
      setMessages((m) => m.map((mm) => mm.actions ? { ...mm, actions: mm.actions.map((a) => a.id === action.id ? { ...a, _done: "accepted" } : a) } : mm));
    } catch (e) {
      const detail = formatError(e);
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "error", content: detail }]);
      toast.error(detail);
    } finally {
      setBusy(false);
    }
  }, [sessionId, runDirective]);

  const declineAction = useCallback((action) => {
    setMessages((m) => m.map((mm) => mm.actions ? { ...mm, actions: mm.actions.map((a) => a.id === action.id ? { ...a, _done: "declined" } : a) } : mm));
  }, []);

  const send = useCallback(async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    const userTurn = { id: crypto.randomUUID(), role: "user", content: msg };
    setMessages((m) => [...m, userTurn]);
    setBusy(true);
    try {
      const res = await api.post("/assistant/chat", {
        session_id: sessionId,
        message: msg,
        page_context: pageContext,
      });
      const d = res.data;
      if (d.session_id !== sessionId) {
        setSessionId(d.session_id);
        saveSessionId(d.session_id);
      }
      const assistantTurn = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: d.reply_text,
        actions: d.proposed_actions || [],
      };
      setMessages((m) => [...m, assistantTurn]);
      // Auto-run tier="auto" actions immediately
      for (const a of (d.proposed_actions || [])) {
        if (a.tier === "auto") {
          await execAction(a, d.session_id);
        }
      }
    } catch (e) {
      const status = e?.response?.status;
      const detail = formatError(e);
      if (status === 402) {
        // Out-of-funds — render an in-panel card with TWO escapes so the user
        // is never stranded on the assistant view.
        const m = /min \$([0-9.]+)/i.exec(detail || "");
        const minNeeded = m ? Number(m[1]) : 0.005;
        setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "out_of_funds", content: detail, minNeeded }]);
      } else {
        setMessages((m) => [...m, { id: crypto.randomUUID(), role: "system", kind: "error", content: detail }]);
      }
    } finally {
      setBusy(false);
    }
  }, [input, busy, sessionId, pageContext, execAction]);

  // First-open greeting
  useEffect(() => {
    if (open && messages.length === 0) {
      const greet = user
        ? `Hi ${user.first_name || ""} — I'm your Birthright guide. Ask me anything, or say "take me to ___" and I'll get you there.`
        : "Hi — I'm the Birthright guide. Ask me about workshops, merch, partners, or anything on the site. Say \"take me to ___\" and I'll bring you there.";
      setMessages([{ id: "greet", role: "assistant", content: greet, actions: [] }]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-20 right-5 z-40 inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#1A2424] text-[#FAF8F5] shadow-lg hover:shadow-xl transition print:hidden"
        data-testid="assistant-open-btn"
        aria-label="Open AI assistant"
      >
        <Sparkles size={14} strokeWidth={1.5} className="text-[#C9A961]" />
        <span className="text-sm">Ask Birthright</span>
        <kbd className="hidden sm:inline-block ml-1 px-1.5 py-0.5 text-[10px] rounded bg-[#FAF8F5]/10 border border-[#FAF8F5]/20">/</kbd>
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-[60] print:hidden" data-testid="assistant-panel">
      <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
      <div className="absolute right-0 top-0 bottom-0 w-full sm:w-[420px] bg-[#FAF8F5] shadow-2xl flex flex-col">
        <header className="flex items-center justify-between px-5 py-4 border-b border-[#E5E1D8] bg-white">
          <div className="flex items-center gap-2">
            <Sparkles size={16} strokeWidth={1.5} className="text-[#C9A961]" />
            <h2 className="font-serif text-lg">Birthright Concierge</h2>
          </div>
          <div className="flex items-center gap-2">
            {user && (
              <button
                onClick={async () => {
                  try {
                    const r = await api.get("/assistant/my-sessions/last");
                    const rows = r.data.messages || [];
                    if (rows.length === 0) {
                      toast.info("No previous conversation");
                      return;
                    }
                    setSessionId(r.data.session_id);
                    saveSessionId(r.data.session_id);
                    setMessages(rows.map((m) => ({
                      id: m.id,
                      role: m.role,
                      content: m.content,
                      actions: m.proposed_actions || [],
                    })));
                  } catch {
                    toast.error("Couldn't load last conversation");
                  }
                }}
                title="Replay your last conversation"
                aria-label="Replay last conversation"
                className="text-[#5C6B6B] hover:text-[#1A2424]"
                data-testid="assistant-replay-btn"
              >
                <History size={16} strokeWidth={1.5} />
              </button>
            )}
            <button
              onClick={() => setOpen(false)}
              className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border border-[#E5E1D8] bg-white text-[#1A2424] hover:bg-[#F4F1EA] active:bg-[#E5E1D8]"
              data-testid="assistant-close-btn"
              aria-label="Close"
            >
              <X size={14} strokeWidth={1.8} /> Close
            </button>
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4" data-testid="assistant-messages">
          {messages.map((m) => (
            <MessageBubble key={m.id} m={m} onAccept={execAction} onDecline={declineAction} busy={busy} />
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-xs text-[#5C6B6B]" data-testid="assistant-busy">
              <Loader2 size={12} className="animate-spin" /> thinking…
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); send(); }}
          className="border-t border-[#E5E1D8] p-3 bg-white pb-[max(0.75rem,env(safe-area-inset-bottom))]"
          data-testid="assistant-form"
        >
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='Try "take me to the partners list"'
              className="input-field flex-1 text-sm"
              disabled={busy}
              data-testid="assistant-input"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="btn-primary px-3"
              data-testid="assistant-send-btn"
              aria-label="Send"
            >
              <Send size={14} strokeWidth={1.5} />
            </button>
          </div>
          <p className="text-[10px] text-[#5C6B6B] mt-2">
            Press <kbd className="px-1 py-0.5 rounded bg-[#F2EEE7] border border-[#E5E1D8]">/</kbd> anywhere to toggle ·
            actions that change data always ask before running.
          </p>
        </form>
      </div>
    </div>
  );
}

function MessageBubble({ m, onAccept, onDecline, busy }) {
  const navigate = useNavigate();
  if (m.role === "user") {
    return (
      <div className="flex justify-end" data-testid={`assistant-msg-user-${m.id}`}>
        <div className="max-w-[85%] px-3 py-2 rounded-2xl bg-[#476B6B] text-white text-sm">
          {m.content}
        </div>
      </div>
    );
  }
  if (m.role === "system" && m.kind === "out_of_funds") {
    return (
      <div className="rounded-xl border border-[#C9A961] bg-[#FFF8E1] p-3" data-testid={`assistant-out-of-funds-${m.id}`}>
        <div className="flex items-start gap-2 mb-2">
          <Wallet size={14} strokeWidth={1.6} className="text-[#8B7128] mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium text-[#8B7128] text-sm">AI wallet is low</p>
            <p className="text-xs text-[#5C6B6B] mt-1">{m.content}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => navigate("/dashboard/ai-wallet")} className="btn-primary text-xs" data-testid="assistant-out-of-funds-topup">
            Top up now
          </button>
        </div>
      </div>
    );
  }
  if (m.role === "system") {
    const iconCls = m.kind === "error" ? "text-[#9E3C3C]" : m.kind === "ok" ? "text-[#2E5C46]" : "text-[#5C6B6B]";
    const Icon = m.kind === "error" ? AlertCircle : m.kind === "ok" ? CheckCircle2 : ChevronDown;
    return (
      <div className="flex items-start gap-2 text-xs" data-testid={`assistant-msg-system-${m.id}`}>
        <Icon size={12} className={`mt-0.5 ${iconCls} flex-shrink-0`} strokeWidth={1.8} />
        <span className={iconCls}>{m.content}</span>
      </div>
    );
  }
  // assistant
  return (
    <div className="space-y-2" data-testid={`assistant-msg-assistant-${m.id}`}>
      <div className="max-w-[92%] px-3 py-2 rounded-2xl bg-white border border-[#E5E1D8] text-sm whitespace-pre-wrap">
        {m.content}
      </div>
      {Array.isArray(m.actions) && m.actions.filter((a) => a.tier === "confirm").map((a) => (
        <ConfirmCard key={a.id} action={a} onAccept={onAccept} onDecline={onDecline} busy={busy} />
      ))}
    </div>
  );
}

function ConfirmCard({ action, onAccept, onDecline, busy }) {
  return (
    <div className="rounded-xl border border-[#C9A961] bg-[#FFF8E1] p-3 text-sm flex flex-col gap-2" data-testid={`confirm-card-${action.type}`}>
      <div className="flex items-start gap-2">
        <Sparkles size={14} strokeWidth={1.5} className="text-[#8B7128] mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="font-medium text-[#8B7128]">Confirm: {action.label}</p>
          <pre className="text-[10px] text-[#5C6B6B] mt-1 whitespace-pre-wrap break-all bg-white/60 rounded p-2 max-h-32 overflow-auto">
            {JSON.stringify(action.params, null, 2)}
          </pre>
        </div>
      </div>
      <div className="flex gap-2 justify-end">
        {action._done === "accepted" ? (
          <span className="text-xs text-[#2E5C46] inline-flex items-center gap-1" data-testid={`confirm-done-${action.type}`}>
            <CheckCircle2 size={12} /> Done
          </span>
        ) : action._done === "declined" ? (
          <span className="text-xs text-[#5C6B6B] inline-flex items-center gap-1" data-testid={`confirm-declined-${action.type}`}>
            Declined
          </span>
        ) : (
          <>
            <button
              onClick={() => onAccept(action)}
              disabled={busy}
              className="btn-primary text-xs"
              data-testid={`confirm-accept-${action.type}`}
            >
              {busy ? "…" : "Confirm"}
            </button>
            <button
              onClick={() => onDecline(action)}
              disabled={busy}
              className="btn-outline text-xs"
              data-testid={`confirm-decline-${action.type}`}
            >
              No thanks
            </button>
          </>
        )}
      </div>
    </div>
  );
}
