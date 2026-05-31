/* Featured Artists ribbon — shown on Gallery landing.
 *
 * Renders the current month's slate with a beautifully-positioned statement
 * overlay on each hero image. The position is locked server-side per slot
 * (so adjacent slots get visually different placements — top-left, top-right,
 * bottom-left, bottom-right, centered bottom band). Once a month begins, the
 * server never changes a slot's position.
 */
import React from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

const POSITION_CLASS = {
  tl: "top-4 left-4 right-auto bottom-auto text-left",
  tr: "top-4 right-4 left-auto bottom-auto text-right",
  bl: "bottom-4 left-4 right-auto top-auto text-left",
  br: "bottom-4 right-4 left-auto top-auto text-right",
  cb: "bottom-0 left-0 right-0 top-auto text-center px-6 pb-5 pt-10 bg-gradient-to-t from-black/55 to-transparent",
};

function StatementOverlay({ position = "br", statement, accentColor = "flame" }) {
  if (!statement) return null;
  const baseColor = {
    flame: "#9E3C3C", moss: "#476B6B", river: "#3F5C73",
    ochre: "#C9A961", indigo: "#3A3A6B", graphite: "#3A3A3A",
  }[accentColor] || "#9E3C3C";
  const isCenterBand = position === "cb";
  return (
    <div
      data-testid={`featured-statement-overlay-${position}`}
      className={`absolute pointer-events-none ${POSITION_CLASS[position] || POSITION_CLASS.br} max-w-[78%]`}
    >
      <div
        className="font-serif text-white text-base sm:text-lg leading-snug drop-shadow-[0_2px_12px_rgba(0,0,0,0.55)]"
        style={{
          textShadow: isCenterBand ? "none" : "0 1px 8px rgba(0,0,0,0.55)",
        }}
      >
        <span className="inline-block px-2.5 py-1 align-baseline" style={{
          background: isCenterBand ? "transparent" : "rgba(0,0,0,0.35)",
          borderLeft: isCenterBand ? "none" : `2px solid ${baseColor}`,
          backdropFilter: isCenterBand ? "none" : "blur(2px)",
        }}>
          {statement}
        </span>
      </div>
    </div>
  );
}

export default function FeaturedArtistsRibbon({ slots = [], periodLabel }) {
  if (!slots || slots.length === 0) return null;
  return (
    <section className="mt-10 mb-8" data-testid="featured-artists-ribbon">
      <div className="flex items-baseline gap-3 mb-3">
        <Sparkles size={16} strokeWidth={1.2} className="text-[#C9A961]" />
        <h2 className="font-serif text-xl text-[#1A2424]">Featured this month</h2>
        {periodLabel && <span className="text-xs text-[#5C6B6B]">· {periodLabel}</span>}
      </div>
      <div className={`grid grid-cols-1 ${slots.length >= 2 ? "md:grid-cols-2" : ""} ${slots.length >= 3 ? "lg:grid-cols-3" : ""} gap-4`}>
        {slots.map((s) => (
          <Link
            key={s.id}
            to={`/gallery/${s.artist_slug}`}
            data-testid={`featured-slot-${s.artist_slug}`}
            className="relative block aspect-[4/3] bg-[#F4F1EA] overflow-hidden rounded-md group"
          >
            {s.signature_image_url || s.photo_url ? (
              <img
                src={s.signature_image_url || s.photo_url}
                alt={s.display_name || s.artist_display_name}
                className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-700"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-[#5C6B6B] text-sm">
                {s.display_name || s.artist_display_name}
              </div>
            )}
            <StatementOverlay
              position={s.statement_position}
              statement={s.signature_statement}
              accentColor={s.accent_color}
            />
            {s.source === "foundation" && (
              <div className="absolute top-3 left-3 bg-[#C9A961] text-white text-[10px] uppercase tracking-[0.18em] px-2 py-1 rounded">
                Foundation pick
              </div>
            )}
            <div className="absolute bottom-0 left-0 right-0 px-4 py-2 bg-gradient-to-t from-black/40 to-transparent pointer-events-none">
              <p className="font-serif text-white text-sm sm:text-base">
                {s.display_name || s.artist_display_name}
              </p>
              {s.location && <p className="text-[10px] text-white/85">{s.location}</p>}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
