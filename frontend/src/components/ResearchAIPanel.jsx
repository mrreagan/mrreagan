import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Sparkles, X, ClipboardCheck, Telescope, Map as MapIcon, HelpCircle, ScrollText, FileText, Tag, Wand2, FlaskConical } from "lucide-react";
import api from "../lib/api";
import AiOutOfFundsCard, { AiBalancePill } from "./AiOutOfFundsCard";

/**
 * AI Research Collaborator panel — for research partners.
 *
 * Positioned as a peer-level collaborator, not a secretary. Two capability
 * groups: INQUIRY (synthesize, map, generate questions, critique) and
 * DRAFTING (summarize notes, suggest tags, polish). Every call shows the
 * AI billing cost.
 */
const TABS = [
  { v: "synthesize", group: "Inquiry",  icon: Telescope,   label: "Synthesize literature" },
  { v: "landscape",  group: "Inquiry",  icon: MapIcon,     label: "Map the landscape" },
  { v: "questions",  group: "Inquiry",  icon: HelpCircle,  label: "Generate questions" },
  { v: "critique",   group: "Inquiry",  icon: ScrollText,  label: "Critique methodology" },
  { v: "summarize",  group: "Drafting", icon: FileText,    label: "Summarize notes" },
  { v: "tags",       group: "Drafting", icon: Tag,         label: "Suggest tags" },
  { v: "polish",     group: "Drafting", icon: Wand2,       label: "Polish draft" },
];

export default function ResearchAIPanel({ open, onClose, onPickResult }) {
  const [tab, setTab] = useState("synthesize");
  const [balance, setBalance] = useState(null);
  const [outOfFunds, setOutOfFunds] = useState(null); // {min} | null
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    setOutOfFunds(null);
    api.get("/ai-wallet/me").then((r) => setBalance(r.data?.wallet?.balance_usd ?? 0)).catch(() => setBalance(null));
  }, [open]);

  // Shared 402 catcher — every pane calls this on errors. If it's a balance
  // issue, set the panel-level out-of-funds card (with a back-to-page button)
  // instead of letting an opaque toast strand the user.
  const handleErr = (e) => {
    const status = e?.response?.status;
    const detail = e?.response?.data?.detail || e?.message || "Failed";
    if (status === 402) {
      const m = /min \$([0-9.]+)/i.exec(detail);
      setOutOfFunds({ min: m ? Number(m[1]) : 0.01 });
      return;
    }
    toast.error(detail);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex" data-testid="research-ai-panel">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="ml-auto relative bg-[#0F2424] text-[#FAF8F5] w-full sm:w-[640px] h-full shadow-2xl flex flex-col">
        <header className="px-5 py-4 border-b border-[#1F3A3A] bg-[#0A1A1A]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FlaskConical size={16} strokeWidth={1.5} className="text-[#C9A961]" />
              <h2 className="font-serif text-lg !text-[#FAF8F5]">Research Collaborator</h2>
            </div>
            <div className="flex items-center gap-2">
              {balance != null && (
                <AiBalancePill balance={balance} onTopup={() => { onClose(); navigate("/dashboard/ai-wallet"); }} />
              )}
              <button onClick={onClose} aria-label="Close" data-testid="research-ai-close" className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border border-[#1F3A3A] bg-[#1A2424] text-[#FAF8F5] hover:bg-[#243333]">
                <X size={13} strokeWidth={1.8} /> Close
              </button>
            </div>
          </div>
          <p className="text-xs text-[#FAF8F5]/60 mt-1">
            A peer collaborator for synthesis, landscape mapping, methodological critique, and drafting.
            Billed at 1× passthrough from your AI Wallet.
          </p>
        </header>

        <div className="px-5 pt-3" data-testid="research-ai-tabs">
          {["Inquiry", "Drafting"].map((g) => (
            <div key={g} className="mt-2">
              <p className="label text-[#C9A961]">{g}</p>
              <div className="flex flex-wrap gap-2 mt-1">
                {TABS.filter((t) => t.group === g).map((t) => {
                  const Icon = t.icon;
                  return (
                    <button
                      key={t.v}
                      onClick={() => setTab(t.v)}
                      className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition inline-flex items-center gap-1 ${
                        tab === t.v ? "bg-[#C9A961] text-[#0F2424] border-[#C9A961]" : "bg-[#1A2424] border-[#1F3A3A] text-[#FAF8F5] hover:border-[#C9A961]"
                      }`}
                      data-testid={`research-ai-tab-${t.v}`}
                    >
                      <Icon size={11} strokeWidth={1.6} /> {t.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5 bg-[#FAF8F5] text-[#1A2424]">
          {outOfFunds && <AiOutOfFundsCard balance={balance} minNeeded={outOfFunds.min} onClose={onClose} />}
          {tab === "synthesize" && <SynthesizePane onErr={handleErr} onPickResult={onPickResult} />}
          {tab === "landscape" && <LandscapePane onErr={handleErr} />}
          {tab === "questions" && <QuestionsPane onErr={handleErr} />}
          {tab === "critique" && <CritiquePane onErr={handleErr} />}
          {tab === "summarize" && <SummarizePane onErr={handleErr} onPickResult={onPickResult} />}
          {tab === "tags" && <TagsPane onErr={handleErr} onPickResult={onPickResult} />}
          {tab === "polish" && <PolishPane onErr={handleErr} onPickResult={onPickResult} />}
        </div>
      </div>
    </div>
  );
}

function CostPill({ cost }) {
  if (cost == null) return null;
  return <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B]" data-testid="cost-pill">billed ${cost.toFixed(4)}</span>;
}

function MarkdownPane({ text }) {
  if (!text) return null;
  return (
    <div className="card p-4 mt-3 bg-white" data-testid="markdown-result">
      <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">{text}</pre>
    </div>
  );
}

// ============ INQUIRY PANES ============

function SynthesizePane({ onErr, onPickResult }) {
  const [topic, setTopic] = useState("");
  const [lens, setLens] = useState("");
  const [depth, setDepth] = useState("standard");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setOut(null);
    try {
      const r = await api.post("/research-collab/synthesize-literature", { topic, lens, depth });
      setOut(r.data.markdown); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Topic</label>
      <input value={topic} onChange={(e) => setTopic(e.target.value)} className="input-field text-sm w-full" placeholder="e.g., disorganized attachment in adoptive families" data-testid="synth-topic" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">Lens to prioritize (optional)</label>
      <input value={lens} onChange={(e) => setLens(e.target.value)} className="input-field text-sm w-full" placeholder="e.g., neurobiology, intergenerational trauma, ethnography" data-testid="synth-lens" />
      <div className="grid grid-cols-2 gap-3 mt-3">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Depth</label>
          <select value={depth} onChange={(e) => setDepth(e.target.value)} className="input-field text-sm w-full" data-testid="synth-depth">
            <option value="brief">Brief (~250 words)</option>
            <option value="standard">Standard (~600 words)</option>
            <option value="deep">Deep (~1200 words)</option>
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={busy || topic.length < 4} className="btn-primary text-sm flex-1" data-testid="synth-run">
            {busy ? "Synthesizing…" : "Synthesize"}
          </button>
        </div>
      </div>
      <div className="mt-2"><CostPill cost={cost} /></div>
      <MarkdownPane text={out} />
      {out && onPickResult && (
        <button onClick={() => onPickResult(out)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="synth-pick">
          <ClipboardCheck size={11} /> Drop into abstract
        </button>
      )}
    </div>
  );
}

function LandscapePane({ onErr }) {
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setData(null);
    try {
      const r = await api.post("/research-collab/map-landscape", { topic });
      setData(r.data); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Topic</label>
      <input value={topic} onChange={(e) => setTopic(e.target.value)} className="input-field text-sm w-full" data-testid="landscape-topic" />
      <button onClick={run} disabled={busy || topic.length < 4} className="btn-primary text-sm mt-3" data-testid="landscape-run">
        {busy ? "Mapping…" : "Map landscape"}
      </button>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {data && data.error && <div className="card p-3 mt-3 bg-[#FFF8E1] text-sm">Topic out of scope: {data.suggestion}</div>}
      {data && !data.error && (
        <div className="space-y-4 mt-3" data-testid="landscape-result">
          {data.key_concepts?.length > 0 && <Section title="Key concepts" items={data.key_concepts.map((c) => `${c.name} — ${c.one_line}`)} />}
          {data.seminal_works_or_authors?.length > 0 && <Section title="Seminal works / authors" items={data.seminal_works_or_authors.map((s) => `${s.name} (${s.era}) — ${s.why}`)} />}
          {data.modern_voices?.length > 0 && <Section title="Modern voices" items={data.modern_voices.map((m) => `${m.name} — ${m.current_focus}`)} />}
          {data.live_debates?.length > 0 && <Section title="Live debates" items={data.live_debates.map((d) => `${d.label}: ${(d.sides || []).join(" vs ")}`)} />}
          {data.recent_shifts?.length > 0 && <Section title="Recent shifts" items={data.recent_shifts.map((s) => `${s.shift} (since ${s.since})`)} />}
          {data.adjacent_fields?.length > 0 && <Section title="Adjacent fields" items={data.adjacent_fields.map((a) => `${a.field} — ${a.what_they_add}`)} />}
        </div>
      )}
    </div>
  );
}

function Section({ title, items }) {
  return (
    <div className="card p-3 bg-white">
      <p className="label text-[#476B6B]">{title}</p>
      <ul className="mt-1 space-y-1 text-sm list-disc pl-5">
        {items.map((t, idx) => <li key={idx}>{t}</li>)}
      </ul>
    </div>
  );
}

function QuestionsPane({ onErr }) {
  const [domain, setDomain] = useState("");
  const [understanding, setUnderstanding] = useState("");
  const [count, setCount] = useState(6);
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setData(null);
    try {
      const r = await api.post("/research-collab/generate-questions", { domain, current_understanding: understanding, count: Number(count) });
      setData(r.data); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Domain</label>
      <input value={domain} onChange={(e) => setDomain(e.target.value)} className="input-field text-sm w-full" placeholder="e.g., relational repair in kinship-care families" data-testid="q-domain" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">What you already know (optional)</label>
      <textarea value={understanding} onChange={(e) => setUnderstanding(e.target.value)} rows={5} className="input-field text-sm w-full" data-testid="q-understanding" />
      <div className="grid grid-cols-2 gap-3 mt-3">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1"># of questions</label>
          <input type="number" min="3" max="12" value={count} onChange={(e) => setCount(e.target.value)} className="input-field text-sm w-full" data-testid="q-count" />
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={busy || domain.length < 4} className="btn-primary text-sm flex-1" data-testid="q-run">
            {busy ? "Surfacing…" : "Generate"}
          </button>
        </div>
      </div>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {data?.questions?.length > 0 && (
        <ul className="space-y-3 mt-3" data-testid="q-result">
          {data.questions.map((q, idx) => (
            <li key={idx} className="card p-3 bg-white">
              <p className="font-serif text-base">{q.question}</p>
              <p className="text-xs text-[#5C6B6B] mt-1"><b>Why underexplored:</b> {q.why_underexplored}</p>
              {q.suggested_methods?.length > 0 && (
                <p className="text-xs text-[#5C6B6B] mt-1"><b>Methods:</b> {q.suggested_methods.join(", ")}</p>
              )}
              {q.natural_collaborators?.length > 0 && (
                <p className="text-xs text-[#5C6B6B] mt-1"><b>Collaborators:</b> {q.natural_collaborators.join(", ")}</p>
              )}
              <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium ${
                q.feasibility === "high" ? "bg-[#E8F0EA] text-[#2E5C46]" :
                q.feasibility === "low"  ? "bg-[#F8DCDC] text-[#7E2C2C]" :
                                            "bg-[#FFF8E1] text-[#8B7128]"
              }`}>{q.feasibility} feasibility</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CritiquePane({ onErr }) {
  const [text, setText] = useState("");
  const [focus, setFocus] = useState("full");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setOut(null);
    try {
      const r = await api.post("/research-collab/critique-methodology", { draft_text: text, focus });
      setOut(r.data.markdown); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Draft text (methods / findings)</label>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={12} className="input-field text-sm w-full" data-testid="crit-text" />
      <div className="grid grid-cols-2 gap-3 mt-3">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Focus</label>
          <select value={focus} onChange={(e) => setFocus(e.target.value)} className="input-field text-sm w-full" data-testid="crit-focus">
            <option value="full">Methods + findings</option>
            <option value="methods_only">Methods only</option>
            <option value="findings_only">Findings only</option>
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={busy || text.length < 80} className="btn-primary text-sm flex-1" data-testid="crit-run">
            {busy ? "Reviewing…" : "Critique"}
          </button>
        </div>
      </div>
      <div className="mt-2"><CostPill cost={cost} /></div>
      <MarkdownPane text={out} />
    </div>
  );
}

// ============ DRAFTING PANES ============

function SummarizePane({ onErr, onPickResult }) {
  const [notes, setNotes] = useState("");
  const [target, setTarget] = useState(180);
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setOut(null);
    try {
      const r = await api.post("/research-collab/summarize-notes", { notes, target_words: Number(target) });
      setOut(r.data.summary); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Working notes</label>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={8} className="input-field text-sm w-full" data-testid="summ-notes" />
      <div className="grid grid-cols-2 gap-3 mt-3">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Target words</label>
          <input type="number" min="80" max="400" value={target} onChange={(e) => setTarget(e.target.value)} className="input-field text-sm w-full" data-testid="summ-target" />
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={busy || notes.length < 20} className="btn-primary text-sm flex-1" data-testid="summ-run">
            {busy ? "…" : "Summarize"}
          </button>
        </div>
      </div>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {out && (
        <div className="card p-3 mt-3 bg-white" data-testid="summ-result">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">{out}</pre>
          {onPickResult && (
            <button onClick={() => onPickResult(out)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="summ-pick">
              <ClipboardCheck size={11} /> Drop into abstract
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function TagsPane({ onErr, onPickResult }) {
  const [title, setTitle] = useState("");
  const [abstract, setAbstract] = useState("");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setData(null);
    try {
      const r = await api.post("/research-collab/suggest-tags", { title, abstract });
      setData(r.data); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Title</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} className="input-field text-sm w-full" data-testid="tags-title" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">Abstract</label>
      <textarea value={abstract} onChange={(e) => setAbstract(e.target.value)} rows={6} className="input-field text-sm w-full" data-testid="tags-abstract" />
      <button onClick={run} disabled={busy || title.length < 3 || abstract.length < 10} className="btn-primary text-sm mt-3" data-testid="tags-run">
        {busy ? "…" : "Suggest tags"}
      </button>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {data && (
        <div className="card p-3 mt-3 bg-white" data-testid="tags-result">
          <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">Tags</p>
          <div className="flex flex-wrap gap-1 mt-1">{(data.tags || []).map((t) => <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-[#F4F1EA]">{t}</span>)}</div>
          <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-3">Categories</p>
          <div className="flex flex-wrap gap-1 mt-1">{(data.categories || []).map((c) => <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-[#E8F0EA] text-[#2E5C46]">{c}</span>)}</div>
          {onPickResult && (
            <button onClick={() => onPickResult(data)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="tags-pick">
              <ClipboardCheck size={11} /> Apply these
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function PolishPane({ onErr, onPickResult }) {
  const [text, setText] = useState("");
  const [style, setStyle] = useState("academic");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setOut(null);
    try {
      const r = await api.post("/research-collab/polish-draft", { text, style });
      setOut(r.data.polished); setCost(r.data.cost_usd);
    } catch (e) { onErr(e); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Draft text</label>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} className="input-field text-sm w-full" data-testid="polish-text" />
      <div className="grid grid-cols-2 gap-3 mt-3">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Style</label>
          <select value={style} onChange={(e) => setStyle(e.target.value)} className="input-field text-sm w-full" data-testid="polish-style">
            <option value="academic">Academic</option>
            <option value="plain">Plain language</option>
            <option value="practitioner">Practitioner</option>
          </select>
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={busy || text.length < 20} className="btn-primary text-sm flex-1" data-testid="polish-run">
            {busy ? "Polishing…" : "Polish"}
          </button>
        </div>
      </div>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {out && (
        <div className="card p-3 mt-3 bg-white" data-testid="polish-result">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">{out}</pre>
          {onPickResult && (
            <button onClick={() => onPickResult(out)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="polish-pick">
              <ClipboardCheck size={11} /> Use this
            </button>
          )}
        </div>
      )}
    </div>
  );
}
