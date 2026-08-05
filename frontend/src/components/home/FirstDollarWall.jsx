import React, { useEffect, useState } from "react";
import api from "../../lib/api";

/**
 * FirstDollarWall — an auto-scrolling social-proof strip of recent
 * first-time supporters. Reads `GET /api/first-dollar/recent`, which
 * returns first-name + last-initial only (no PII crosses the boundary).
 *
 * Hidden entirely if the backend returns no first-purchases yet — the
 * homepage shouldn't sport an empty ticker in a pre-launch state.
 */

function relativeTimeShort(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffSec = Math.max(1, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  const m = Math.floor(diffSec / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  const w = Math.floor(d / 7);
  if (w < 5) return `${w}w ago`;
  const mo = Math.floor(d / 30);
  return `${mo}mo ago`;
}

export default function FirstDollarWall() {
  const [items, setItems] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let alive = true;
    api.get("/first-dollar/recent?limit=16")
      .then((r) => {
        if (!alive) return;
        setItems(Array.isArray(r.data) ? r.data : []);
        setLoaded(true);
      })
      .catch(() => alive && setLoaded(true));
    return () => { alive = false; };
  }, []);

  if (!loaded || items.length === 0) return null;

  // Duplicate the item list so the CSS translate loop reads seamlessly.
  const track = [...items, ...items];

  return (
    <section
      className="bg-[#FAF7F0] border-y border-[#E5E1D8] py-4 overflow-hidden"
      data-testid="first-dollar-wall"
    >
      <div className="container-page">
        <div className="flex items-center gap-3 text-[11px] uppercase tracking-wider text-[#476B6B] font-semibold mb-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C9A961] animate-pulse" />
          First-Dollar Wall · new supporters
        </div>
      </div>

      <div
        className="relative"
        style={{
          maskImage: "linear-gradient(to right, transparent 0, black 5%, black 95%, transparent 100%)",
          WebkitMaskImage: "linear-gradient(to right, transparent 0, black 5%, black 95%, transparent 100%)",
        }}
      >
        <div
          className="flex gap-8 whitespace-nowrap first-dollar-track"
          style={{
            animation: `fdw-scroll ${Math.max(20, items.length * 4)}s linear infinite`,
            width: "max-content",
          }}
          data-testid="first-dollar-track"
        >
          {track.map((entry, i) => (
            <span
              key={`${entry.at}-${i}`}
              className="inline-flex items-center gap-2 text-sm text-[#0F2424]"
            >
              <span className="text-[#C9A961]">◆</span>
              <span className="font-semibold">{entry.display_name}</span>
              <span className="text-[#5C6B6B]">
                claimed their first
              </span>
              <span className="font-semibold text-[#476B6B] max-w-[240px] truncate">
                {entry.item_label}
              </span>
              <span className="text-[#5C6B6B]">·</span>
              <span className="text-[#5C6B6B]">{relativeTimeShort(entry.at)}</span>
            </span>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes fdw-scroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
        .first-dollar-track:hover {
          animation-play-state: paused !important;
        }
        @media (prefers-reduced-motion: reduce) {
          .first-dollar-track {
            animation: none !important;
            transform: none !important;
          }
        }
      `}</style>
    </section>
  );
}
