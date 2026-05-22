import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { Calendar, MapPin, Users, Star, Clock, ChevronDown, Sparkles } from "lucide-react";
import { toast } from "sonner";

const formatDateTime = (iso) => {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-US", { dateStyle: "full", timeStyle: "short" });
};

const formatDate = (iso) => {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
};

// Build .ics file for the workshop
function downloadIcs(w) {
  const fmt = (d) => new Date(d).toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
  const ics = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//birthright//workshop//EN
BEGIN:VEVENT
UID:${w.id}@birthright.live
DTSTAMP:${fmt(new Date())}
DTSTART:${fmt(w.start_date)}
DTEND:${fmt(w.end_date)}
SUMMARY:${w.title}
DESCRIPTION:${(w.short_description || "").replace(/\n/g, " ")}
LOCATION:${w.location_name}, ${w.location_address}
END:VEVENT
END:VCALENDAR`;
  const blob = new Blob([ics], { type: "text/calendar" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${w.slug}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function WorkshopDetail() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [w, setW] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [reviews, setReviews] = useState([]);
  const [publicImpacts, setPublicImpacts] = useState([]);
  const [registered, setRegistered] = useState(false);
  const [waitlisted, setWaitlisted] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState(null);

  useEffect(() => {
    api
      .get(`/workshops/${slug}`)
      .then((r) => {
        setW(r.data);
        api.get(`/reviews?workshop_id=${r.data.id}`).then((rr) => setReviews(rr.data)).catch(() => {});
        api.get(`/impact-statements?workshop_id=${r.data.id}&public_only=true`).then((ii) => setPublicImpacts(ii.data)).catch(() => {});
        if (user) {
          api.get(`/workshops/${r.data.id}/my-registration`).then((mr) => setRegistered(mr.data.registered)).catch(() => {});
        }
      })
      .catch(() => {});
  }, [slug, user]);

  if (!w) return <div className="container-page py-20" data-testid="workshop-loading">Loading workshop...</div>;

  const isEarlyBird = w.early_bird_until && new Date(w.early_bird_until) > new Date();
  const currentPrice = isEarlyBird ? w.early_bird_price : w.regular_price;
  const isFull = w.spots_left <= 0;
  const isPast = w.status === "completed";

  const register = async () => {
    if (!user) {
      toast.info("Please sign in to register");
      navigate("/login", { state: { from: `/workshops/${slug}` } });
      return;
    }
    setRegistering(true);
    try {
      const { data } = await api.post("/checkout/workshop", {
        workshop_id: w.id,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setRegistering(false);
    }
  };

  const joinWaitlist = async () => {
    if (!user) {
      navigate("/login", { state: { from: `/workshops/${slug}` } });
      return;
    }
    try {
      const { data } = await api.post(`/workshops/${w.id}/waitlist`, {});
      setWaitlisted(true);
      toast.success(data.message);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not join waitlist");
    }
  };

  const avgRating = reviews.length ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1) : null;

  return (
    <div data-testid="workshop-detail-page">
      {/* HERO */}
      <section className="bg-white border-b border-[#E5E1D8]">
        <div className="container-page py-12 grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-7">
            <span className="label">{w.status === "upcoming" ? "Upcoming workshop" : w.status === "completed" ? "Past workshop" : w.status}</span>
            <h1 className="editorial-h1 mt-3" data-testid="workshop-title">{w.title}</h1>
            <p className="text-lg text-[#5C6B6B] mt-5 leading-relaxed">{w.short_description}</p>
            {avgRating && (
              <div className="flex items-center gap-2 mt-5">
                <div className="flex">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star key={s} size={16} strokeWidth={1.5} className={s <= Math.round(avgRating) ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"} />
                  ))}
                </div>
                <span className="text-sm text-[#1A2424] font-medium">{avgRating}</span>
                <span className="text-xs text-[#5C6B6B]">({reviews.length} {reviews.length === 1 ? "review" : "reviews"})</span>
              </div>
            )}
            <div className="mt-8 grid grid-cols-2 gap-4 max-w-md">
              <div>
                <span className="label">When</span>
                <p className="text-sm text-[#1A2424] mt-1.5 flex items-start gap-2"><Calendar size={14} strokeWidth={1.5} className="text-[#C9A961] mt-0.5" />{formatDate(w.start_date)}</p>
              </div>
              <div>
                <span className="label">Where</span>
                <p className="text-sm text-[#1A2424] mt-1.5 flex items-start gap-2"><MapPin size={14} strokeWidth={1.5} className="text-[#C9A961] mt-0.5" />{w.location_name}</p>
              </div>
              {w.status === "upcoming" && (
                <div>
                  <span className="label">Capacity</span>
                  <p className="text-sm text-[#1A2424] mt-1.5 flex items-start gap-2"><Users size={14} strokeWidth={1.5} className="text-[#C9A961] mt-0.5" />{w.spots_left} of {w.capacity} spots</p>
                </div>
              )}
              {w.facilitator && (
                <div>
                  <span className="label">Facilitated by</span>
                  <Link to={`/facilitators/${w.facilitator.facilitator_slug || w.facilitator.id}`} className="text-sm text-[#476B6B] mt-1.5 block hover:underline">{w.facilitator.first_name} {w.facilitator.last_name}</Link>
                </div>
              )}
            </div>
          </div>
          <div className="lg:col-span-5">
            <div className="card overflow-hidden sticky top-24" data-testid="workshop-register-card">
              <div className="aspect-[4/3]">
                <img src={w.image_url} alt={w.title} className="w-full h-full object-cover" />
              </div>
              <div className="p-6">
                {!isPast ? (
                  <>
                    {isEarlyBird && (
                      <div className="mb-3">
                        <span className="label text-[#C9A961]">Early-bird pricing</span>
                        <p className="text-xs text-[#5C6B6B] mt-1">Ends {formatDate(w.early_bird_until)}</p>
                      </div>
                    )}
                    <div className="flex items-baseline gap-3">
                      <span className="font-serif text-4xl text-[#1A2424]" data-testid="workshop-price">${currentPrice?.toFixed(0)}</span>
                      {isEarlyBird && <span className="text-base text-[#5C6B6B] line-through">${w.regular_price?.toFixed(0)}</span>}
                    </div>
                    {registered ? (
                      <Link to={`/dashboard/workshops/${w.id}`} className="btn-primary w-full justify-center mt-5" data-testid="workshop-go-to-hub">
                        Go to workshop hub
                      </Link>
                    ) : isFull ? (
                      <button onClick={joinWaitlist} disabled={waitlisted} className="btn-outline w-full justify-center mt-5" data-testid="workshop-waitlist">
                        {waitlisted ? "On the waitlist" : "Join the waitlist"}
                      </button>
                    ) : (
                      <button onClick={register} disabled={registering} className="btn-primary w-full justify-center mt-5" data-testid="workshop-register-btn">
                        {registering ? "Loading..." : "Register"}
                      </button>
                    )}
                    {registered && (
                      <button onClick={() => downloadIcs(w)} className="btn-outline w-full justify-center mt-3 text-sm" data-testid="workshop-add-calendar">
                        Add to Calendar
                      </button>
                    )}
                  </>
                ) : (
                  <>
                    <span className="label">This workshop has ended</span>
                    <p className="text-sm text-[#5C6B6B] mt-2">Read past participant impact below or browse upcoming.</p>
                    <Link to="/workshops" className="btn-primary w-full justify-center mt-5">Browse upcoming</Link>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* BODY */}
      <section className="container-page py-16 grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-8 space-y-12">
          <div>
            <span className="label">About this workshop</span>
            <p className="text-base text-[#1A2424] mt-4 leading-relaxed whitespace-pre-line">{w.full_description}</p>
          </div>

          {w.materials_included?.length > 0 && (
            <div>
              <span className="label">What's included</span>
              <ul className="mt-4 space-y-2">
                {w.materials_included.map((m) => (
                  <li key={m} className="flex items-start gap-3 text-sm text-[#1A2424]">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C9A961] mt-2 shrink-0" />
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {w.faq?.length > 0 && (
            <div data-testid="workshop-faq">
              <span className="label">Frequently asked</span>
              <div className="mt-4 space-y-3">
                {w.faq.map((item, i) => (
                  <div key={item.q} className="card overflow-hidden">
                    <button
                      onClick={() => setExpandedFaq(expandedFaq === i ? null : i)}
                      className="w-full p-5 flex items-start justify-between text-left"
                      data-testid={`faq-toggle-${i}`}
                    >
                      <span className="font-medium text-[#1A2424] pr-4">{item.q}</span>
                      <ChevronDown size={18} strokeWidth={1.5} className={`text-[#5C6B6B] shrink-0 transition-transform ${expandedFaq === i ? "rotate-180" : ""}`} />
                    </button>
                    {expandedFaq === i && (
                      <div className="px-5 pb-5 text-sm text-[#5C6B6B] leading-relaxed border-t border-[#E5E1D8] pt-4">{item.a}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {reviews.length > 0 && (
            <div data-testid="workshop-reviews">
              <span className="label">Reviews</span>
              <div className="mt-4 space-y-4">
                {reviews.slice(0, 5).map((r) => (
                  <div key={r.id} className="card p-6">
                    <div className="flex items-center gap-3 justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex">
                          {[1, 2, 3, 4, 5].map((s) => (
                            <Star key={s} size={14} strokeWidth={1.5} className={s <= r.rating ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"} />
                          ))}
                        </div>
                        <span className="text-xs label">{r.user_name}</span>
                      </div>
                    </div>
                    <p className="text-sm text-[#1A2424] mt-3 leading-relaxed">{r.review_text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {publicImpacts.length > 0 && (
            <div>
              <span className="label">Impact in their own words</span>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {publicImpacts.slice(0, 4).map((imp) => (
                  <div key={imp.id} className="card p-6">
                    <Sparkles size={18} strokeWidth={1.5} className="text-[#C9A961]" />
                    <p className="font-serif text-lg mt-3 leading-snug">"{imp.what_learned}"</p>
                    <p className="text-xs text-[#5C6B6B] mt-3 label">— {imp.user_name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="lg:col-span-4">
          <div className="card p-6 sticky top-24">
            <span className="label">Location</span>
            <p className="text-sm text-[#1A2424] mt-2 font-medium">{w.location_name}</p>
            <p className="text-sm text-[#5C6B6B] mt-1">{w.location_address}</p>
            {w.map_url && (
              <a href={w.map_url} target="_blank" rel="noreferrer" className="text-sm text-[#476B6B] font-medium mt-3 inline-block hover:underline" data-testid="workshop-map-link">
                Open in maps →
              </a>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}
