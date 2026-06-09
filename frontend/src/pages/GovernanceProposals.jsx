import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { Vote, FileText, ShieldCheck, AlertCircle, Clock } from "lucide-react";

const CATEGORY_LABEL = {
  rev_share: "Revenue share",
  policy: "Policy",
  membership: "Membership",
  indemnification: "Legal",
  other: "Other",
};

const STATUS_BADGE = {
  open: { label: "Open", className: "bg-[#2E5C46]/10 text-[#2E5C46] border-[#2E5C46]/30" },
  passed: { label: "Passed", className: "bg-[#C9A961]/15 text-[#8B7128] border-[#C9A961]/40" },
  failed: { label: "Failed", className: "bg-[#B86A5C]/10 text-[#B86A5C] border-[#B86A5C]/30" },
  withdrawn: { label: "Withdrawn", className: "bg-[#5C6B6B]/10 text-[#5C6B6B] border-[#5C6B6B]/30" },
  draft: { label: "Draft", className: "bg-[#E5E1D8] text-[#5C6B6B] border-[#5C6B6B]/30" },
};

function StatusPill({ status }) {
  const c = STATUS_BADGE[status] || STATUS_BADGE.draft;
  return (
    <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider border rounded-full ${c.className}`}>
      {c.label}
    </span>
  );
}

function fmtDate(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }); }
  catch { return iso; }
}

export default function GovernanceProposals() {
  const { user } = useAuth();
  const isMember = !!user && (user.role === "admin" || user.governance_member);
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showNew, setShowNew] = useState(false);
  const [selected, setSelected] = useState(null);

  const load = () => {
    setLoading(true);
    api.get("/governance/proposals")
      .then((r) => setProposals(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = filter === "all" ? proposals : proposals.filter((p) => p.status === filter);

  return (
    <div className="container-page py-12" data-testid="governance-proposals-page">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <span className="label">Governance</span>
          <h1 className="editorial-h1 mt-2">Proposals & voting</h1>
        </div>
        {isMember && (
          <button
            onClick={() => setShowNew(true)}
            className="btn-primary"
            data-testid="new-proposal-btn"
          >
            Propose a change
          </button>
        )}
      </div>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Birthright is governed in the open. Anyone can read every proposal, debate, and outcome. Governance members vote; the ombudsman can close votes early when needed.
      </p>

      <div className="flex flex-wrap gap-2 mt-6" data-testid="proposal-status-filters">
        {["all", "open", "passed", "failed", "withdrawn"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              filter === s ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`filter-${s}`}
          >
            {s === "all" ? "All" : STATUS_BADGE[s]?.label || s}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-3" data-testid="proposals-list">
        {loading ? (
          <p className="text-sm text-[#5C6B6B]">Loading proposals…</p>
        ) : filtered.length === 0 ? (
          <div className="card p-10 text-center">
            <Vote size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
            <p className="font-serif text-lg mt-3">No proposals yet in this view.</p>
          </div>
        ) : (
          filtered.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelected(p)}
              className="card p-5 text-left w-full hover:border-[#476B6B] transition"
              data-testid={`proposal-row-${p.id}`}
            >
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">{CATEGORY_LABEL[p.category] || p.category}</p>
                    <StatusPill status={p.status} />
                  </div>
                  <h3 className="font-serif text-lg mt-1">{p.title}</h3>
                  <p className="text-sm text-[#5C6B6B] mt-1 line-clamp-2">{p.summary}</p>
                </div>
                <div className="text-right text-xs text-[#5C6B6B] shrink-0">
                  <p><Clock size={11} strokeWidth={1.5} className="inline mr-1" />Closes {fmtDate(p.voting_closes_at)}</p>
                  <p className="mt-1">{p.yes_count} yes · {p.no_count} no · {p.abstain_count} abstain</p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>

      {selected && (
        <ProposalDetailModal
          proposal={selected}
          isMember={isMember}
          isAdmin={user?.role === "admin"}
          isOmbudsman={user?.is_ombudsman}
          onClose={() => setSelected(null)}
          onUpdate={(p) => { setSelected(p); load(); }}
        />
      )}
      {showNew && (
        <NewProposalModal
          onClose={() => setShowNew(false)}
          onCreated={() => { setShowNew(false); load(); }}
        />
      )}

      <div className="mt-12 card p-6 bg-[#FAF8F5] border-[#E5E1D8]" data-testid="legal-cta">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <span className="label inline-flex items-center gap-1"><FileText size={11} strokeWidth={1.5} /> Legal</span>
            <h3 className="font-serif text-xl mt-1">Universal indemnification agreement</h3>
            <p className="text-sm text-[#5C6B6B] mt-1 max-w-xl">
              Every birthright participant and partner is asked to review and sign one universal agreement. Read the current version, see what's changed, and sign.
            </p>
          </div>
          <Link to="/legal/indemnification" className="btn-outline" data-testid="view-indemnification-link">
            Review & sign
          </Link>
        </div>
      </div>
    </div>
  );
}

function NewProposalModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ title: "", summary: "", body: "", category: "policy", implementation_notes: "" });
  const [busy, setBusy] = useState(false);
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/governance/proposals", form);
      toast.success("Proposal submitted");
      onCreated();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit proposal");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#1A2424]/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="new-proposal-modal">
      <div className="bg-white w-full max-w-2xl rounded-xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-2xl">New proposal</h2>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#1A2424]" data-testid="close-new-proposal">✕</button>
        </div>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <div>
            <label className="label">Title</label>
            <input className="input-field" value={form.title} onChange={(e) => update("title", e.target.value)} required minLength={5} maxLength={200} data-testid="proposal-title" />
          </div>
          <div>
            <label className="label">Category</label>
            <select className="input-field" value={form.category} onChange={(e) => update("category", e.target.value)} data-testid="proposal-category">
              <option value="rev_share">Revenue share</option>
              <option value="policy">Policy</option>
              <option value="membership">Membership</option>
              <option value="indemnification">Legal / Indemnification</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="label">One-line summary</label>
            <input className="input-field" value={form.summary} onChange={(e) => update("summary", e.target.value)} required minLength={10} maxLength={500} data-testid="proposal-summary" />
          </div>
          <div>
            <label className="label">Body (context, rationale, what should change)</label>
            <textarea className="input-field min-h-[180px]" value={form.body} onChange={(e) => update("body", e.target.value)} required minLength={20} maxLength={20000} data-testid="proposal-body" />
          </div>
          <div>
            <label className="label">Implementation notes (optional)</label>
            <textarea className="input-field" value={form.implementation_notes} onChange={(e) => update("implementation_notes", e.target.value)} maxLength={5000} data-testid="proposal-impl" />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={busy} data-testid="submit-proposal">{busy ? "Submitting…" : "Submit for vote"}</button>
            <button type="button" className="btn-outline" onClick={onClose}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ProposalDetailModal({ proposal, isMember, isAdmin, isOmbudsman, onClose, onUpdate }) {
  const [votes, setVotes] = useState([]);
  const [myVote, setMyVote] = useState(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return;
    api.get(`/governance/proposals/${proposal.id}/votes`)
      .then((r) => {
        setVotes(r.data);
        const mine = r.data.find((v) => v.voter_id === user.id);
        if (mine) { setMyVote(mine.vote); setComment(mine.comment || ""); }
      })
      .catch(() => {});
  }, [proposal.id, user]);

  const cast = async (vote) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/governance/proposals/${proposal.id}/vote`, { vote, comment });
      toast.success(`Recorded "${vote}"`);
      setMyVote(vote);
      onUpdate({ ...proposal, yes_count: data.yes_count, no_count: data.no_count, abstain_count: data.abstain_count });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not vote");
    } finally { setBusy(false); }
  };

  const close = async () => {
    if (!window.confirm("Close voting and tally the result?")) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/governance/proposals/${proposal.id}/close`, {});
      toast.success(`Proposal ${data.status}`);
      onUpdate(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not close");
    } finally { setBusy(false); }
  };

  const isOpen = proposal.status === "open";
  const canClose = isOpen && (isAdmin || isOmbudsman || user?.id === proposal.proposer_id);

  return (
    <div className="fixed inset-0 z-50 bg-[#1A2424]/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid={`proposal-detail-${proposal.id}`}>
      <div className="bg-white w-full max-w-3xl rounded-xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">{CATEGORY_LABEL[proposal.category] || proposal.category}</span>
              <StatusPill status={proposal.status} />
            </div>
            <h2 className="font-serif text-2xl mt-2">{proposal.title}</h2>
            <p className="text-xs text-[#5C6B6B] mt-1">
              Proposed by {proposal.proposer_name} · {fmtDate(proposal.created_at)} · Closes {fmtDate(proposal.voting_closes_at)}
            </p>
          </div>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#1A2424]" data-testid="close-proposal-detail">✕</button>
        </div>
        <div className="mt-4">
          <p className="font-medium">{proposal.summary}</p>
          <pre className="text-sm mt-3 whitespace-pre-wrap font-sans">{proposal.body}</pre>
          {proposal.implementation_notes && (
            <div className="mt-4 bg-[#FAF8F5] border border-[#E5E1D8] p-3 rounded">
              <span className="label">Implementation</span>
              <p className="text-sm mt-1 whitespace-pre-wrap">{proposal.implementation_notes}</p>
            </div>
          )}
        </div>

        {/* Tally */}
        <div className="mt-6 grid grid-cols-3 gap-2 text-center" data-testid="vote-tally">
          {[
            { k: "yes_count", label: "Yes", color: "#2E5C46" },
            { k: "no_count", label: "No", color: "#B86A5C" },
            { k: "abstain_count", label: "Abstain", color: "#5C6B6B" },
          ].map((c) => (
            <div key={c.k} className="border border-[#E5E1D8] rounded p-3">
              <p className="font-serif text-3xl" style={{ color: c.color }}>{proposal[c.k]}</p>
              <p className="text-[10px] uppercase tracking-wider">{c.label}</p>
            </div>
          ))}
        </div>

        {isOpen && isMember && (
          <div className="mt-6 border-t border-[#E5E1D8] pt-4" data-testid="vote-controls">
            <span className="label">Your vote {myVote && <span className="text-[#C9A961]">(current: {myVote})</span>}</span>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Optional comment for the record"
              className="input-field mt-2"
              maxLength={2000}
              data-testid="vote-comment"
            />
            <div className="flex gap-2 mt-3">
              {["yes", "no", "abstain"].map((v) => (
                <button
                  key={v}
                  onClick={() => cast(v)}
                  disabled={busy}
                  className={`btn-outline capitalize ${myVote === v ? "ring-2 ring-[#C9A961]" : ""}`}
                  data-testid={`cast-${v}`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
        )}

        {!isMember && isOpen && (
          <p className="text-xs text-[#5C6B6B] mt-4 italic">
            <AlertCircle size={11} strokeWidth={1.5} className="inline mr-1" />
            Only governance members can vote. The full discussion remains public.
          </p>
        )}

        {canClose && (
          <button onClick={close} disabled={busy} className="btn-outline mt-4" data-testid="close-proposal-btn">
            {user?.id === proposal.proposer_id && !isAdmin && !isOmbudsman ? "Withdraw proposal" : "Close & tally"}
          </button>
        )}

        {/* Vote log */}
        <div className="mt-6 border-t border-[#E5E1D8] pt-4">
          <span className="label inline-flex items-center gap-1"><ShieldCheck size={11} strokeWidth={1.5} /> Votes on record</span>
          {votes.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] mt-2">No votes yet.</p>
          ) : (
            <ul className="mt-2 divide-y divide-[#E5E1D8]" data-testid="votes-log">
              {votes.map((v) => (
                <li key={v.id} className="py-2 text-sm flex items-start justify-between gap-3">
                  <div>
                    <span className="font-medium">{v.voter_name}</span>{" "}
                    <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">{v.vote}</span>
                    {v.comment && <p className="text-xs text-[#5C6B6B] mt-0.5 whitespace-pre-wrap">{v.comment}</p>}
                  </div>
                  <span className="text-[10px] text-[#5C6B6B] shrink-0">{fmtDate(v.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
