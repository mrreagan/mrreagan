import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { Users, MessageCircle, LifeBuoy, ArrowRight, Calendar } from "lucide-react";
import { toast } from "sonner";

const formatDate = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

export default function FacilitatorDashboard() {
  const [workshops, setWorkshops] = useState([]);
  const [selected, setSelected] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [qa, setQa] = useState([]);
  const [support, setSupport] = useState([]);
  const [response, setResponse] = useState({});

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

  const markAnswered = async (id) => {
    await api.post(`/discussions/${id}/mark-answered`);
    setQa((prev) => prev.map((q) => (q.id === id ? { ...q, answered: true } : q)));
    toast.success("Marked answered");
  };

  const respondSupport = async (id) => {
    const text = response[id];
    if (!text) return;
    await api.post(`/support-requests/${id}/respond`, { response: text });
    setResponse((prev) => ({ ...prev, [id]: "" }));
    api.get(`/support-requests?workshop_id=${selected.id}`).then((r) => setSupport(r.data));
    toast.success("Response sent");
  };

  return (
    <div className="container-page py-12" data-testid="facilitator-dashboard-page">
      <span className="label">Facilitator dashboard</span>
      <h1 className="editorial-h1 mt-2">Your workshops</h1>
      <div className="divider-flame" />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-8">
        <aside className="lg:col-span-1 space-y-2" data-testid="fac-workshop-list">
          {workshops.map((w) => (
            <button
              key={w.id}
              onClick={() => setSelected(w)}
              className={`w-full text-left card p-4 transition ${
                selected?.id === w.id ? "border-[#476B6B] bg-[#FAF8F5]" : ""
              }`}
              data-testid={`fac-workshop-${w.id}`}
            >
              <div className="text-xs text-[#5C6B6B] inline-flex items-center gap-1">
                <Calendar size={11} strokeWidth={1.5} />{formatDate(w.start_date)}
              </div>
              <p className="font-serif text-base mt-1 leading-tight">{w.title}</p>
              <div className="mt-2 flex gap-3 text-[10px] text-[#5C6B6B] uppercase tracking-wider">
                <span><Users size={10} strokeWidth={1.5} className="inline mb-0.5" /> {w.registered_count}</span>
                {w.open_qa > 0 && <span className="text-[#C9A961]">{w.open_qa} Q&A</span>}
                {w.open_support > 0 && <span className="text-[#9E3C3C]">{w.open_support} support</span>}
              </div>
            </button>
          ))}
        </aside>

        <div className="lg:col-span-3 space-y-6">
          {!selected ? (
            <div className="card p-12 text-center text-sm text-[#5C6B6B]">No workshops assigned yet.</div>
          ) : (
            <>
              <div className="card p-7">
                <h2 className="font-serif text-2xl">{selected.title}</h2>
                <div className="mt-4 grid grid-cols-3 gap-4 text-center">
                  <div className="border-r border-[#E5E1D8]">
                    <p className="font-serif text-3xl text-[#476B6B]">{participants.length}</p>
                    <p className="label mt-1">Registered</p>
                  </div>
                  <div className="border-r border-[#E5E1D8]">
                    <p className="font-serif text-3xl text-[#476B6B]">{qa.filter((q) => !q.answered).length}</p>
                    <p className="label mt-1">Open Q&A</p>
                  </div>
                  <div>
                    <p className="font-serif text-3xl text-[#476B6B]">{support.filter((s) => s.status !== "resolved").length}</p>
                    <p className="label mt-1">Open Support</p>
                  </div>
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link to={`/workshops/${selected.slug}`} className="btn-outline text-sm">View public page</Link>
                  <span className="px-4 py-2 rounded-full bg-[#FAF8F5] border border-[#E5E1D8] text-sm">
                    <span className="label text-[#5C6B6B]">Check-in code:</span> <strong className="ml-2 tracking-wider">{selected.check_in_code}</strong>
                  </span>
                </div>
              </div>

              {/* Participants */}
              <div className="card p-7" data-testid="fac-participants">
                <h3 className="font-serif text-xl">Participants ({participants.length})</h3>
                <div className="mt-4 space-y-2">
                  {participants.length === 0 && <p className="text-sm text-[#5C6B6B]">No registrations yet.</p>}
                  {participants.map((p) => (
                    <div key={p.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-[#FAF8F5]">
                      <div>
                        <p className="text-sm font-medium">{p.user?.first_name} {p.user?.last_name}</p>
                        <p className="text-xs text-[#5C6B6B]">{p.user?.email} · {p.pricing_tier}</p>
                      </div>
                      {p.checked_in && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#2E5C46]/10 text-[#2E5C46]">Checked in</span>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Q&A */}
              <div className="card p-7" data-testid="fac-qa">
                <h3 className="font-serif text-xl">Open Q&A</h3>
                <div className="mt-4 space-y-3">
                  {qa.filter((q) => !q.answered).length === 0 && <p className="text-sm text-[#5C6B6B]">No open questions.</p>}
                  {qa.filter((q) => !q.answered).map((q) => (
                    <div key={q.id} className="border border-[#E5E1D8] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-[#5C6B6B]">
                        <span><strong className="text-[#1A2424]">{q.user_name}</strong>{q.is_private && " · Private"}</span>
                        <button onClick={() => markAnswered(q.id)} className="text-[#2E5C46] hover:underline">Mark answered</button>
                      </div>
                      <p className="text-sm mt-2 whitespace-pre-line">{q.content}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Support */}
              <div className="card p-7" data-testid="fac-support">
                <h3 className="font-serif text-xl">Support requests</h3>
                <div className="mt-4 space-y-3">
                  {support.length === 0 && <p className="text-sm text-[#5C6B6B]">No requests.</p>}
                  {support.map((s) => (
                    <div key={s.id} className="border border-[#E5E1D8] rounded-xl p-4">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-sm">{s.subject}</p>
                        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${s.status === "resolved" ? "bg-[#2E5C46]/10 text-[#2E5C46]" : "bg-[#C9A961]/15 text-[#C9A961]"}`}>{s.status}</span>
                      </div>
                      <p className="text-xs text-[#5C6B6B] mt-1">From {s.user_name}</p>
                      <p className="text-sm mt-2 whitespace-pre-line">{s.content}</p>
                      {s.response ? (
                        <div className="mt-3 pt-3 border-t border-[#E5E1D8] text-sm">
                          <p className="label">Your reply</p>
                          <p className="mt-1 whitespace-pre-line">{s.response}</p>
                        </div>
                      ) : (
                        <div className="mt-3 flex gap-2">
                          <textarea
                            rows={2}
                            value={response[s.id] || ""}
                            onChange={(e) => setResponse({ ...response, [s.id]: e.target.value })}
                            placeholder="Type a reply…"
                            className="input-field text-sm resize-none flex-1"
                            data-testid={`support-reply-${s.id}`}
                          />
                          <button onClick={() => respondSupport(s.id)} className="btn-primary text-sm" data-testid={`support-send-${s.id}`}>Send</button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
