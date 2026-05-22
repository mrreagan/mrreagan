import React from "react";
import { Link } from "react-router-dom";
import { Calendar, MapPin, Users, Star, ChevronDown, Sparkles } from "lucide-react";

export const formatDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : "";

// ---------- Star rating ----------
export function StarRow({ rating, size = 16 }) {
  return (
    <div className="flex">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          size={size}
          strokeWidth={1.5}
          className={s <= Math.round(rating) ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"}
        />
      ))}
    </div>
  );
}

// ---------- Workshop hero header ----------
export function WorkshopHero({ workshop, avgRating, reviewCount }) {
  return (
    <div className="lg:col-span-7">
      <span className="label">
        {workshop.status === "upcoming"
          ? "Upcoming workshop"
          : workshop.status === "completed"
          ? "Past workshop"
          : workshop.status}
      </span>
      <h1 className="editorial-h1 mt-3" data-testid="workshop-title">
        {workshop.title}
      </h1>
      <p className="text-lg text-[#5C6B6B] mt-5 leading-relaxed">{workshop.short_description}</p>
      {avgRating && (
        <div className="flex items-center gap-2 mt-5">
          <StarRow rating={avgRating} />
          <span className="text-sm text-[#1A2424] font-medium">{avgRating}</span>
          <span className="text-xs text-[#5C6B6B]">
            ({reviewCount} {reviewCount === 1 ? "review" : "reviews"})
          </span>
        </div>
      )}
      <WorkshopMetaGrid workshop={workshop} />
    </div>
  );
}

function WorkshopMetaGrid({ workshop }) {
  return (
    <div className="mt-8 grid grid-cols-2 gap-4 max-w-md">
      <MetaCell label="When" icon={Calendar}>
        {formatDate(workshop.start_date)}
      </MetaCell>
      <MetaCell label="Where" icon={MapPin}>
        {workshop.location_name}
      </MetaCell>
      {workshop.status === "upcoming" && (
        <MetaCell label="Capacity" icon={Users}>
          {workshop.spots_left} of {workshop.capacity} spots
        </MetaCell>
      )}
      {workshop.facilitator && (
        <div>
          <span className="label">Facilitated by</span>
          <Link
            to={`/facilitators/${workshop.facilitator.facilitator_slug || workshop.facilitator.id}`}
            className="text-sm text-[#476B6B] mt-1.5 block hover:underline"
          >
            {workshop.facilitator.first_name} {workshop.facilitator.last_name}
          </Link>
        </div>
      )}
    </div>
  );
}

function MetaCell({ label, icon: Icon, children }) {
  return (
    <div>
      <span className="label">{label}</span>
      <p className="text-sm text-[#1A2424] mt-1.5 flex items-start gap-2">
        <Icon size={14} strokeWidth={1.5} className="text-[#C9A961] mt-0.5" />
        {children}
      </p>
    </div>
  );
}

// ---------- Materials included list ----------
export function MaterialsList({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <span className="label">What's included</span>
      <ul className="mt-4 space-y-2">
        {items.map((m) => (
          <li key={m} className="flex items-start gap-3 text-sm text-[#1A2424]">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C9A961] mt-2 shrink-0" />
            {m}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------- FAQ accordion ----------
export function WorkshopFaq({ faq, expandedIdx, onToggle }) {
  if (!faq || faq.length === 0) return null;
  return (
    <div data-testid="workshop-faq">
      <span className="label">Frequently asked</span>
      <div className="mt-4 space-y-3">
        {faq.map((item, i) => (
          <div key={item.q} className="card overflow-hidden">
            <button
              onClick={() => onToggle(i)}
              className="w-full p-5 flex items-start justify-between text-left"
              data-testid={`faq-toggle-${i}`}
            >
              <span className="font-medium text-[#1A2424] pr-4">{item.q}</span>
              <ChevronDown
                size={18}
                strokeWidth={1.5}
                className={`text-[#5C6B6B] shrink-0 transition-transform ${expandedIdx === i ? "rotate-180" : ""}`}
              />
            </button>
            {expandedIdx === i && (
              <div className="px-5 pb-5 text-sm text-[#5C6B6B] leading-relaxed border-t border-[#E5E1D8] pt-4">
                {item.a}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Reviews list ----------
export function ReviewsList({ reviews }) {
  if (!reviews || reviews.length === 0) return null;
  return (
    <div data-testid="workshop-reviews">
      <span className="label">Reviews</span>
      <div className="mt-4 space-y-4">
        {reviews.slice(0, 5).map((r) => (
          <div key={r.id} className="card p-6">
            <div className="flex items-center gap-3 justify-between">
              <div className="flex items-center gap-2">
                <StarRow rating={r.rating} size={14} />
                <span className="text-xs label">{r.user_name}</span>
              </div>
            </div>
            <p className="text-sm text-[#1A2424] mt-3 leading-relaxed">{r.review_text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Public impact preview ----------
export function PublicImpactPreview({ impacts }) {
  if (!impacts || impacts.length === 0) return null;
  return (
    <div>
      <span className="label">Impact in their own words</span>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {impacts.slice(0, 4).map((imp) => (
          <div key={imp.id} className="card p-6">
            <Sparkles size={18} strokeWidth={1.5} className="text-[#C9A961]" />
            <p className="font-serif text-lg mt-3 leading-snug">"{imp.what_learned}"</p>
            <p className="text-xs text-[#5C6B6B] mt-3 label">— {imp.user_name}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Location sidebar ----------
export function LocationCard({ workshop }) {
  return (
    <aside className="lg:col-span-4">
      <div className="card p-6 sticky top-24">
        <span className="label">Location</span>
        <p className="text-sm text-[#1A2424] mt-2 font-medium">{workshop.location_name}</p>
        <p className="text-sm text-[#5C6B6B] mt-1">{workshop.location_address}</p>
        {workshop.map_url && (
          <a
            href={workshop.map_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-[#476B6B] font-medium mt-3 inline-block hover:underline"
            data-testid="workshop-map-link"
          >
            Open in maps →
          </a>
        )}
      </div>
    </aside>
  );
}
