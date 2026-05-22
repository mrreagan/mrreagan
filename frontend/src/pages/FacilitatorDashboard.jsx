import React, { useEffect, useState, useCallback, useMemo } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { Users, Calendar } from "lucide-react";
import { toast } from "sonner";

const formatDate = (iso) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

// ---------- Workshop sidebar item ----------
function WorkshopSidebarItem({ workshop, isSelected, onSelect }) {
  return (
    <button
      onClick={() => onSelect(workshop)}
      className={`w-full text-left card p-4 transition ${
        isSelected ? "border-[#476B6B] bg-[#FAF8F5]" : ""
      }`}
      data-testid={`fac-workshop-${workshop.id}`}
    >
      <div className="text-xs text-[#5C6B6B] inline-flex items-center gap-1">
        <Calendar size={11} strokeWidth={1.5} />
        {formatDate(workshop.start_date)}
      </div>
      <p className="font-serif text-base mt-1 leading-tight">{workshop.title}</p>
      <div className="mt-2 flex gap-3 text-[10px] text-[#5C6B6B] uppercase tracking-wider">
        <span>
          <Users size={10} strokeWidth={1.5} className="inline mb-0.5" /> {workshop.registered_count}
        </span>
        {workshop.open_qa > 0 && <span className="text-[#C9A961]">{workshop.open_qa} Q&A</span>}
        {workshop.open_support > 0 && <span className="text-[#9E3C3C]">{workshop.open_support} support</span>}
      </div>
    </button>
  );
}

// ---------- Header card with stats and check-in code ----------
function WorkshopHeaderCard({ workshop, participants, qaCount, supportCount }) {
  return (
    <div className="card p-7">
      <h2 className="font-serif text-2xl">{workshop.title}</h2>
      <div className="mt-4 grid grid-cols-3 gap-4 text-center">
        <div className="border-r border-[#E5E1D8]">
          <p className="font-serif text-3xl text-[#476B6B]">{participants.length}</p>
          <p className="label mt-1">Registered</p>
        </div>
        <div className="border-r border-[#E5E1D8]">
          <p className="font-serif text-3xl text-[#476B6B]">{qaCount}</p>
          <p className="label mt-1">Open Q&A</p>
        </div>
        <div>
          <p className="font-serif text-3xl text-[#476B6B]">{supportCount}</p>
          <p className="label mt-1">Open Support</p>
        </div>
      </div>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link to={`/workshops/${workshop.slug}`} className="btn-outline text-sm">
          View public page
        </Link>
        <span className="px-4 py-2 rounded-full bg-[#FAF8F5] border border-[#E5E1D8] text-sm">
          <span className="label text-[#5C6B6B]">Check-in code:</span>{" "}
          <strong className="ml-2 tracking-wider">{workshop.check_in_code}</strong>
        </span>
      </div>
    </div>
  );
}

// ---------- Participants list ----------
function ParticipantsList({ participants, onRelease }) {
  return (
    <div className="card p-7" data-testid="fac-participants">
      <h3 className="font-serif text-xl">Participants ({participants.length})</h3>
      <div className="mt-4 space-y-2">
        {participants.length === 0 && <p className="text-sm text-[#5C6B6B]">No registrations yet.</p>}
        {participants.map((p) => (
          <div key={p.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-[#FAF8F5]">
            <div>
              <p className="text-sm font-medium">
                {p.user?.first_name} {p.user?.last_name}
              </p>
              <p className="text-xs text-[#5C6B6B]">
                {p.user?.email} · {p.pricing_tier}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {p.checked_in ? (
                <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#2E5C46]/10 text-[#2E5C46]">
                  Checked in
                </span>
              ) : (
                <button
                  onClick={() => onRelease(p)}
                  className="text-[11px] text-[#B86A5C] hover:underline"
                  data-testid={`release-seat-${p.id}`}
                  title="Release this seat — the next person on the waitlist will be notified"
                >
                  Release seat
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Open Q&A list ----------
function OpenQaList({ openQa, onMarkAnswered }) {
  return (
    <div className="card p-7" data-testid="fac-qa">
      <h3 className="font-serif text-xl">Open Q&A</h3>
      <div className="mt-4 space-y-3">
        {openQa.length === 0 && <p className="text-sm text-[#5C6B6B]">No open questions.</p>}
        {openQa.map((q) => (
          <div key={q.id} className="border border-[#E5E1D8] rounded-xl p-4">
            <div className="flex items-center justify-between text-xs text-[#5C6B6B]">
              <span>
                <strong className="text-[#1A2424]">{q.user_name}</strong>
                {q.is_private && " · Private"}
              </span>
              <button onClick={() => onMarkAnswered(q.id)} className="text-[#2E5C46] hover:underline">
                Mark answered
              </button>
            </div>
            <p className="text-sm mt-2 whitespace-pre-line">{q.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Single support request item ----------
function SupportRequestItem({ request, replyValue, onReplyChange, onSendReply }) {
  return (
    <div className="border border-[#E5E1D8] rounded-xl p-4">
      <div className="flex items-center justify-between">
        <p className="font-medium text-sm">{request.subject}</p>
        <span
          className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${
            request.status === "resolved"
              ? "bg-[#2E5C46]/10 text-[#2E5C46]"
              : "bg-[#C9A961]/15 text-[#C9A961]"
          }`}
        >
          {request.status}
        </span>
      </div>
      <p className="text-xs text-[#5C6B6B] mt-1">From {request.user_name}</p>
      <p className="text-sm mt-2 whitespace-pre-line">{request.content}</p>
      {request.response ? (
        <div className="mt-3 pt-3 border-t border-[#E5E1D8] text-sm">
          <p className="label">Your reply</p>
          <p className="mt-1 whitespace-pre-line">{request.response}</p>
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          <textarea
            rows={2}
            value={replyValue}
            onChange={(e) => onReplyChange(request.id, e.target.value)}
            placeholder="Type a reply…"
            className="input-field text-sm resize-none flex-1"
            data-testid={`support-reply-${request.id}`}
          />
          <button
            onClick={() => onSendReply(request.id)}
            className="btn-primary text-sm"
            data-testid={`support-send-${request.id}`}
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
}

// ---------- Support requests list ----------
function SupportRequestList({ supportRequests, replies, onReplyChange, onSendReply }) {
  return (
    <div className="card p-7" data-testid="fac-support">
      <h3 className="font-serif text-xl">Support requests</h3>
      <div className="mt-4 space-y-3">
        {supportRequests.length === 0 && <p className="text-sm text-[#5C6B6B]">No requests.</p>}
        {supportRequests.map((s) => (
          <SupportRequestItem
            key={s.id}
            request={s}
            replyValue={replies[s.id] || ""}
            onReplyChange={onReplyChange}
            onSendReply={onSendReply}
          />
        ))}
      </div>
    </div>
  );
}

// ---------- Selected workshop detail panel ----------
function WorkshopDetailPanel({ workshop, participants, qa, support, replies, onMarkAnswered, onReplyChange, onSendReply, onRelease }) {
  const openQa = useMemo(() => qa.filter((q) => !q.answered), [qa]);
  const openSupportCount = useMemo(
    () => support.filter((s) => s.status !== "resolved").length,
    [support]
  );

  return (
    <div className="space-y-6">
      <WorkshopHeaderCard
        workshop={workshop}
        participants={participants}
        qaCount={openQa.length}
        supportCount={openSupportCount}
      />
      <ParticipantsList participants={participants} onRelease={onRelease} />
      <OpenQaList openQa={openQa} onMarkAnswered={onMarkAnswered} />
      <SupportRequestList
        supportRequests={support}
        replies={replies}
        onReplyChange={onReplyChange}
        onSendReply={onSendReply}
      />
    </div>
  );
}

// ---------- Main component ----------
export default function FacilitatorDashboard() {
  const [workshops, setWorkshops] = useState([]);
  const [selected, setSelected] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [qa, setQa] = useState([]);
  const [support, setSupport] = useState([]);
  const [replies, setReplies] = useState({});

  useEffect(() => {
    api.get("/dashboard/facilitator").then((r) => {
      setWorkshops(r.data.workshops);
      if (r.data.workshops.length > 0) setSelected(r.data.workshops[0]);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.get(`/workshops/${selected.id}/participants`).then((r) => setParticipants(r.data)).catch(() => {});
    api.get(`/discussions?workshop_id=${selected.id}&is_question=true`).then((r) => setQa(r.data)).catch(() => {});
    api.get(`/support-requests?workshop_id=${selected.id}`).then((r) => setSupport(r.data)).catch(() => {});
  }, [selected]);

  const markAnswered = useCallback(async (id) => {
    await api.post(`/discussions/${id}/mark-answered`);
    setQa((prev) => prev.map((q) => (q.id === id ? { ...q, answered: true } : q)));
    toast.success("Marked answered");
  }, []);

  const handleReplyChange = useCallback((id, value) => {
    setReplies((prev) => ({ ...prev, [id]: value }));
  }, []);

  const respondSupport = useCallback(async (id) => {
    const text = replies[id];
    if (!text || !selected) return;
    await api.post(`/support-requests/${id}/respond`, { response: text });
    setReplies((prev) => ({ ...prev, [id]: "" }));
    const r = await api.get(`/support-requests?workshop_id=${selected.id}`);
    setSupport(r.data);
    toast.success("Response sent");
  }, [replies, selected]);

  const releaseSeat = useCallback(async (registration) => {
    const name = `${registration.user?.first_name || ""} ${registration.user?.last_name || ""}`.trim() || "this participant";
    if (!window.confirm(`Release the seat held by ${name}? The first person on the waitlist will be notified by email.`)) return;
    try {
      const res = await api.post(`/registrations/${registration.id}/release`);
      setParticipants((prev) => prev.filter((p) => p.id !== registration.id));
      toast.success(res.data?.promoted ? "Seat released. Waitlist promoted." : "Seat released.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not release seat");
    }
  }, []);

  return (
    <div className="container-page py-12" data-testid="facilitator-dashboard-page">
      <span className="label">Facilitator dashboard</span>
      <h1 className="editorial-h1 mt-2">Your workshops</h1>
      <div className="divider-flame" />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-8">
        <aside className="lg:col-span-1 space-y-2" data-testid="fac-workshop-list">
          {workshops.map((w) => (
            <WorkshopSidebarItem key={w.id} workshop={w} isSelected={selected?.id === w.id} onSelect={setSelected} />
          ))}
        </aside>

        <div className="lg:col-span-3">
          {!selected ? (
            <div className="card p-12 text-center text-sm text-[#5C6B6B]">No workshops assigned yet.</div>
          ) : (
            <WorkshopDetailPanel
              workshop={selected}
              participants={participants}
              qa={qa}
              support={support}
              replies={replies}
              onMarkAnswered={markAnswered}
              onReplyChange={handleReplyChange}
              onSendReply={respondSupport}
              onRelease={releaseSeat}
            />
          )}
        </div>
      </div>
    </div>
  );
}
