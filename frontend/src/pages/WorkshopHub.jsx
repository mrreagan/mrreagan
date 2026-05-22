import React, { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { useCart } from "../contexts/CartContext";
import { toast } from "sonner";
import { MapPin, MessageCircle, MessageSquare, HelpCircle, ShoppingBag, Star, Sparkles, LifeBuoy, CheckCircle2, Send } from "lucide-react";

const TABS = [
  { id: "directions", label: "Directions & Check-in", icon: MapPin },
  { id: "discussion", label: "Discussion", icon: MessageSquare },
  { id: "qa", label: "Q&A", icon: HelpCircle },
  { id: "chat", label: "Chat", icon: MessageCircle },
  { id: "materials", label: "Materials", icon: ShoppingBag },
  { id: "review", label: "Review", icon: Star },
  { id: "impact", label: "Impact", icon: Sparkles },
  { id: "support", label: "Support", icon: LifeBuoy },
];

export default function WorkshopHub() {
  const { id } = useParams();
  const { user } = useAuth();
  const [workshop, setWorkshop] = useState(null);
  const [reg, setReg] = useState(null);
  const [tab, setTab] = useState("directions");

  useEffect(() => {
    api.get(`/workshops/${id}`).then((r) => setWorkshop(r.data));
    api.get(`/workshops/${id}/my-registration`).then((r) => setReg(r.data));
  }, [id]);

  if (!workshop || !reg) return <div className="container-page py-20" data-testid="hub-loading">Loading...</div>;
  if (!reg.registered) {
    return (
      <div className="container-page py-20 text-center">
        <p>You're not registered for this workshop.</p>
        <Link to="/workshops" className="btn-primary mt-4 inline-flex">Browse workshops</Link>
      </div>
    );
  }

  return (
    <div className="container-page py-12" data-testid="workshop-hub-page">
      <Link to="/dashboard" className="text-sm text-[#5C6B6B] hover:text-[#476B6B]">← Dashboard</Link>
      <span className="label mt-4 block">Workshop hub</span>
      <h1 className="editorial-h1 mt-2" data-testid="hub-title">{workshop.title}</h1>
      <p className="text-sm text-[#5C6B6B] mt-3">
        With {workshop.facilitator?.first_name} {workshop.facilitator?.last_name} ·{" "}
        {new Date(workshop.start_date).toLocaleDateString("en-US", { dateStyle: "long" })}
      </p>

      <div className="mt-8 border-b border-[#E5E1D8] overflow-x-auto no-scrollbar" data-testid="hub-tabs">
        <div className="flex gap-1 min-w-max">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
                tab === t.id ? "border-[#476B6B] text-[#476B6B]" : "border-transparent text-[#5C6B6B] hover:text-[#1A2424]"
              }`}
              data-testid={`hub-tab-${t.id}`}
            >
              <t.icon size={15} strokeWidth={1.5} /> {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8">
        {tab === "directions" && <DirectionsTab workshop={workshop} reg={reg} />}
        {tab === "discussion" && <DiscussionTab workshop={workshop} type="discussion" />}
        {tab === "qa" && <DiscussionTab workshop={workshop} type="qa" user={user} />}
        {tab === "chat" && <ChatTab workshop={workshop} user={user} />}
        {tab === "materials" && <MaterialsTab workshop={workshop} />}
        {tab === "review" && <ReviewTab workshop={workshop} />}
        {tab === "impact" && <ImpactTab workshop={workshop} />}
        {tab === "support" && <SupportTab workshop={workshop} />}
      </div>
    </div>
  );
}

// ---------- DIRECTIONS & CHECK-IN ----------
function DirectionsTab({ workshop, reg }) {
  const [code, setCode] = useState("");
  const [checkedIn, setCheckedIn] = useState(reg.registration?.checked_in || false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post(`/workshops/${workshop.id}/check-in`, { code });
      setCheckedIn(true);
      toast.success("You're checked in.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Invalid code");
    } finally {
      setLoading(false);
    }
  };

  // QR code via external service
  const qrText = `BIRTHRIGHT|${workshop.id}|${reg.registration?.id}`;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(qrText)}`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="tab-directions">
      <div className="lg:col-span-2 card p-7">
        <span className="label">Where to go</span>
        <h3 className="font-serif text-2xl mt-2">{reg.location_name}</h3>
        <p className="text-sm text-[#5C6B6B] mt-1">{reg.location_address}</p>
        {reg.map_url && (
          <a href={reg.map_url} target="_blank" rel="noreferrer" className="btn-outline mt-4 inline-flex text-sm">
            Open in maps
          </a>
        )}
        {reg.directions_notes && (
          <>
            <span className="label mt-7 block">Notes from the facilitator</span>
            <p className="text-sm text-[#1A2424] mt-3 leading-relaxed whitespace-pre-line">{reg.directions_notes}</p>
          </>
        )}
      </div>
      <div className="card p-7" data-testid="check-in-card">
        {checkedIn ? (
          <>
            <CheckCircle2 size={48} strokeWidth={1.5} className="text-[#2E5C46]" />
            <h3 className="font-serif text-2xl mt-4">You're checked in.</h3>
            <p className="text-sm text-[#5C6B6B] mt-2">Welcome. Find a seat and breathe.</p>
          </>
        ) : (
          <>
            <span className="label">Check-in</span>
            <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">
              Once you arrive, your facilitator will share a check-in code. Or show them this QR code.
            </p>
            <div className="my-5 flex justify-center">
              <img src={qrUrl} alt="Check-in QR" className="rounded-lg border border-[#E5E1D8]" data-testid="check-in-qr" />
            </div>
            <form onSubmit={submit} className="space-y-3">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Enter check-in code"
                className="input-field text-center uppercase tracking-widest"
                data-testid="check-in-code-input"
              />
              <button type="submit" disabled={loading || !code} className="btn-primary w-full justify-center" data-testid="check-in-submit">
                {loading ? "..." : "Check in"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

// ---------- DISCUSSION / Q&A ----------
function DiscussionTab({ workshop, type, user }) {
  const [items, setItems] = useState([]);
  const [content, setContent] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const isQuestion = type === "qa";

  const load = () => {
    api.get(`/discussions?workshop_id=${workshop.id}&is_question=${isQuestion}`).then((r) => setItems(r.data));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workshop.id, type]);

  const submit = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      await api.post("/discussions", {
        workshop_id: workshop.id,
        content,
        is_question: isQuestion,
        is_private: isPrivate,
      });
      setContent("");
      setIsPrivate(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not post");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid={`tab-${type}`}>
      <div className="lg:col-span-2 space-y-3">
        {items.length === 0 && (
          <div className="card p-8 text-center text-sm text-[#5C6B6B]">
            {isQuestion ? "No questions yet. Be the first to ask." : "No posts yet. Be the first."}
          </div>
        )}
        {items.map((it) => (
          <div key={it.id} className="card p-5" data-testid={`disc-${it.id}`}>
            <div className="flex items-center justify-between text-xs text-[#5C6B6B]">
              <span><strong className="text-[#1A2424]">{it.user_name}</strong> · {it.user_role}</span>
              <div className="flex gap-2">
                {it.is_private && <span className="bg-[#C9A961]/15 text-[#C9A961] px-2 py-0.5 rounded-full">Private</span>}
                {it.answered && <span className="bg-[#2E5C46]/10 text-[#2E5C46] px-2 py-0.5 rounded-full">Answered</span>}
              </div>
            </div>
            <p className="text-sm text-[#1A2424] mt-3 leading-relaxed whitespace-pre-line">{it.content}</p>
            <p className="text-xs text-[#5C6B6B] mt-3">{new Date(it.created_at).toLocaleString()}</p>
          </div>
        ))}
      </div>
      <div className="card p-5 h-fit sticky top-24">
        <span className="label">{isQuestion ? "Ask a question" : "Start a thread"}</span>
        <form onSubmit={submit} className="mt-3 space-y-3">
          <textarea
            rows={5}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={isQuestion ? "What would you like to ask?" : "Share with the cohort"}
            className="input-field resize-none"
            data-testid={`${type}-textarea`}
          />
          {isQuestion && (
            <label className="flex items-center gap-2 text-xs text-[#5C6B6B]">
              <input
                type="checkbox"
                checked={isPrivate}
                onChange={(e) => setIsPrivate(e.target.checked)}
                className="accent-[#476B6B]"
                data-testid={`${type}-private`}
              />
              Send privately to facilitator
            </label>
          )}
          <button type="submit" disabled={!content.trim()} className="btn-primary w-full justify-center text-sm" data-testid={`${type}-submit`}>
            <Send size={14} strokeWidth={1.5} /> Post
          </button>
        </form>
      </div>
    </div>
  );
}

// ---------- CHAT (polling) ----------
function ChatTab({ workshop, user }) {
  const [messages, setMessages] = useState([]);
  const [recipientId, setRecipientId] = useState(null); // null = group
  const [participants, setParticipants] = useState([]);
  const [text, setText] = useState("");
  const lastFetchRef = useRef(null);
  const scrollRef = useRef(null);

  const load = async () => {
    const params = new URLSearchParams({ workshop_id: workshop.id });
    if (recipientId) params.append("recipient_id", recipientId);
    if (lastFetchRef.current) params.append("since", lastFetchRef.current);
    const { data } = await api.get(`/chat?${params}`);
    if (data.length) {
      setMessages((prev) => {
        const merged = [...prev, ...data];
        lastFetchRef.current = merged[merged.length - 1].created_at;
        return merged;
      });
    }
  };

  useEffect(() => {
    setMessages([]);
    lastFetchRef.current = null;
    api.get(`/chat/participants?workshop_id=${workshop.id}`).then((r) => setParticipants(r.data));
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recipientId]);

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
    } catch (err) {
      toast.error("Could not send");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6" data-testid="tab-chat">
      <div className="card p-4 lg:max-h-[600px] lg:overflow-y-auto" data-testid="chat-participants">
        <span className="label">Conversations</span>
        <button
          onClick={() => setRecipientId(null)}
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
              onClick={() => setRecipientId(p.id)}
              className={`block w-full text-left px-3 py-2 rounded-lg text-sm ${
                recipientId === p.id ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"
              }`}
              data-testid={`chat-user-${p.id}`}
            >
              {p.name} {p.role === "facilitator" && <span className="text-[10px] uppercase tracking-wider ml-1 opacity-70">facilitator</span>}
            </button>
          ))}
        </div>
      </div>
      <div className="lg:col-span-3 card p-5 flex flex-col" style={{ minHeight: "500px" }}>
        <span className="label">{recipientId ? participants.find((p) => p.id === recipientId)?.name : "Group chat"}</span>
        <div ref={scrollRef} className="flex-1 mt-4 overflow-y-auto space-y-3 max-h-[420px] pr-2" data-testid="chat-messages">
          {messages.length === 0 && <p className="text-sm text-[#5C6B6B] text-center py-10">No messages yet.</p>}
          {messages.map((m) => {
            const mine = m.sender_id === user?.id;
            return (
              <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${mine ? "bg-[#476B6B] text-white" : "bg-[#FAF8F5] text-[#1A2424]"}`}>
                  {!mine && <p className="text-[10px] uppercase tracking-wider opacity-60 mb-0.5">{m.sender_name}</p>}
                  <p className="text-sm">{m.content}</p>
                </div>
              </div>
            );
          })}
        </div>
        <form onSubmit={send} className="mt-4 flex gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type a message"
            className="input-field flex-1"
            data-testid="chat-input"
          />
          <button type="submit" className="btn-primary" data-testid="chat-send">
            <Send size={14} strokeWidth={1.5} />
          </button>
        </form>
      </div>
    </div>
  );
}

// ---------- MATERIALS (gated shop) ----------
function MaterialsTab({ workshop }) {
  const [products, setProducts] = useState([]);
  const { addItem } = useCart();
  useEffect(() => {
    api.get(`/products?workshop_id=${workshop.id}&type=workshop_material`).then((r) => setProducts(r.data));
  }, [workshop.id]);
  return (
    <div data-testid="tab-materials">
      <p className="text-sm text-[#5C6B6B] mb-5">
        These materials are reserved for participants of this workshop.
      </p>
      {products.length === 0 ? (
        <div className="card p-10 text-center text-sm text-[#5C6B6B]">No materials available yet.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {products.map((p) => (
            <div key={p.id} className="card overflow-hidden" data-testid={`material-${p.id}`}>
              <div className="aspect-square bg-[#E5E1D8]">
                <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
              </div>
              <div className="p-5">
                <p className="font-serif text-lg">{p.name}</p>
                <p className="text-xs text-[#5C6B6B] mt-1 line-clamp-2">{p.description}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="font-medium">${p.price?.toFixed(2)}</span>
                  <button
                    onClick={() => { addItem(p); toast.success("Added"); }}
                    className="text-xs flex items-center gap-1.5 bg-[#476B6B] text-white px-3 py-1.5 rounded-full hover:bg-[#3A5858] transition"
                    data-testid={`material-add-${p.id}`}
                  >
                    <ShoppingBag size={12} strokeWidth={1.5} /> Add
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="text-xs text-[#5C6B6B] mt-6">
        Items go to your <Link to="/cart" className="text-[#476B6B] hover:underline">cart</Link>.
      </p>
    </div>
  );
}

// ---------- REVIEW ----------
function ReviewTab({ workshop }) {
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [anon, setAnon] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/reviews", {
        workshop_id: workshop.id,
        rating,
        review_text: text,
        anonymous: anon,
      });
      setSubmitted(true);
      toast.success("Thank you for your review");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit review");
    }
  };

  return (
    <div className="max-w-2xl" data-testid="tab-review">
      <span className="label">Your review</span>
      <h3 className="font-serif text-2xl mt-2">How was this workshop?</h3>
      {submitted ? (
        <div className="card p-8 mt-6 text-center">
          <CheckCircle2 size={36} strokeWidth={1.5} className="text-[#2E5C46] mx-auto" />
          <p className="text-sm text-[#1A2424] mt-3">Your review has been recorded. Thank you.</p>
        </div>
      ) : (
        <form onSubmit={submit} className="card p-7 mt-6 space-y-5">
          <div>
            <label className="label block mb-3">Rating</label>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setRating(s)}
                  className="p-1"
                  data-testid={`review-star-${s}`}
                >
                  <Star size={28} strokeWidth={1.5} className={s <= rating ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"} />
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="label block mb-2">Your review</label>
            <textarea required rows={6} value={text} onChange={(e) => setText(e.target.value)} className="input-field resize-none" data-testid="review-text" />
          </div>
          <label className="flex items-center gap-2 text-sm text-[#5C6B6B]">
            <input type="checkbox" checked={anon} onChange={(e) => setAnon(e.target.checked)} className="accent-[#476B6B]" data-testid="review-anon" />
            Submit anonymously
          </label>
          <button type="submit" className="btn-primary w-full justify-center" data-testid="review-submit">
            Submit review
          </button>
        </form>
      )}
    </div>
  );
}

// ---------- IMPACT STATEMENT ----------
function ImpactTab({ workshop }) {
  const [form, setForm] = useState({
    what_learned: "",
    how_grew: "",
    benefits: "",
    improvements: "",
    is_public: false,
    anonymous: false,
  });
  const [submitted, setSubmitted] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/impact-statements", { ...form, workshop_id: workshop.id });
      setSubmitted(true);
      toast.success("Thank you for sharing.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit");
    }
  };

  return (
    <div className="max-w-3xl" data-testid="tab-impact">
      <span className="label">Personal impact statement</span>
      <h3 className="font-serif text-2xl mt-2">Reflect on your experience.</h3>
      <p className="text-sm text-[#5C6B6B] mt-2">
        For yourself, and — if you choose — for the people considering this workshop.
      </p>
      {submitted ? (
        <div className="card p-8 mt-6 text-center">
          <CheckCircle2 size={36} strokeWidth={1.5} className="text-[#2E5C46] mx-auto" />
          <p className="text-sm text-[#1A2424] mt-3">Saved. You can edit it anytime from your dashboard.</p>
        </div>
      ) : (
        <form onSubmit={submit} className="card p-7 mt-6 space-y-5">
          <div>
            <label className="label block mb-2">What I learned</label>
            <textarea required rows={3} value={form.what_learned} onChange={(e) => setForm({ ...form, what_learned: e.target.value })} className="input-field resize-none" data-testid="impact-learned" />
          </div>
          <div>
            <label className="label block mb-2">How I grew</label>
            <textarea required rows={3} value={form.how_grew} onChange={(e) => setForm({ ...form, how_grew: e.target.value })} className="input-field resize-none" data-testid="impact-grew" />
          </div>
          <div>
            <label className="label block mb-2">How I benefited</label>
            <textarea required rows={3} value={form.benefits} onChange={(e) => setForm({ ...form, benefits: e.target.value })} className="input-field resize-none" data-testid="impact-benefits" />
          </div>
          <div>
            <label className="label block mb-2">Ideas to improve (optional)</label>
            <textarea rows={3} value={form.improvements} onChange={(e) => setForm({ ...form, improvements: e.target.value })} className="input-field resize-none" data-testid="impact-improvements" />
          </div>
          <div className="space-y-2 pt-2 border-t border-[#E5E1D8]">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_public} onChange={(e) => setForm({ ...form, is_public: e.target.checked })} className="accent-[#476B6B]" data-testid="impact-public" />
              Share publicly on the homepage and workshop page (optional)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.anonymous} onChange={(e) => setForm({ ...form, anonymous: e.target.checked })} className="accent-[#476B6B]" data-testid="impact-anonymous" />
              Share anonymously
            </label>
          </div>
          <button type="submit" className="btn-primary w-full justify-center" data-testid="impact-submit">
            Save my impact statement
          </button>
        </form>
      )}
    </div>
  );
}

// ---------- SUPPORT REQUEST ----------
function SupportTab({ workshop }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ subject: "", content: "", urgency: "normal" });

  const load = () => api.get(`/support-requests?workshop_id=${workshop.id}`).then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/support-requests", { ...form, workshop_id: workshop.id });
      setForm({ subject: "", content: "", urgency: "normal" });
      load();
      toast.success("Your support request was sent.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="tab-support">
      <div className="lg:col-span-2 space-y-3">
        {items.length === 0 && <div className="card p-8 text-center text-sm text-[#5C6B6B]">No support requests yet.</div>}
        {items.map((s) => (
          <div key={s.id} className="card p-5" data-testid={`support-${s.id}`}>
            <div className="flex items-center justify-between">
              <p className="font-medium">{s.subject}</p>
              <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${
                s.status === "resolved" ? "bg-[#2E5C46]/10 text-[#2E5C46]" : "bg-[#C9A961]/15 text-[#C9A961]"
              }`}>{s.status}</span>
            </div>
            <p className="text-sm text-[#5C6B6B] mt-2 whitespace-pre-line">{s.content}</p>
            {s.response && (
              <div className="mt-3 border-t border-[#E5E1D8] pt-3 text-sm">
                <p className="text-xs label">Reply from {s.responded_by}</p>
                <p className="text-[#1A2424] mt-1 whitespace-pre-line">{s.response}</p>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="card p-5 h-fit sticky top-24">
        <span className="label">New request</span>
        <form onSubmit={submit} className="mt-3 space-y-3">
          <input required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Subject" className="input-field" data-testid="support-subject" />
          <textarea required rows={5} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="How can we help?" className="input-field resize-none" data-testid="support-content" />
          <select value={form.urgency} onChange={(e) => setForm({ ...form, urgency: e.target.value })} className="input-field" data-testid="support-urgency">
            <option value="low">Low urgency</option>
            <option value="normal">Normal</option>
            <option value="high">High urgency</option>
          </select>
          <button type="submit" className="btn-primary w-full justify-center text-sm" data-testid="support-submit">Send to facilitator</button>
        </form>
      </div>
    </div>
  );
}
