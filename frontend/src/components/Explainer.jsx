import React, { useState, useRef, useEffect } from "react";
import { Info } from "lucide-react";
import explainers from "../data/explainers";

/**
 * Inline info-icon that reveals a board-facing explainer popover on
 * hover (desktop) or click (mobile / touch).
 *
 *   <Explainer id="growth.kpi.foundation_net" />
 *
 * Copy lives centrally in /src/data/explainers.js so writers can iterate
 * without touching component code.
 *
 * Props:
 *   id      key into explainers map (required)
 *   size    icon px (default 12)
 *   className extra classes for the trigger button
 *   dark    render on dark background — flips icon colour
 */
export default function Explainer({ id, size = 12, className = "", dark = false }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const data = explainers[id];

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!data) {
    // Fail visibly in dev, silently in prod
    if (process.env.NODE_ENV !== "production") {
      console.warn(`<Explainer/> missing key: ${id}`);
    }
    return null;
  }

  return (
    <span ref={ref} className={`relative inline-flex align-middle ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      data-testid={`explainer-${id}`}>
      <button
        type="button"
        onClick={(e) => { e.preventDefault(); setOpen((v) => !v); }}
        className={`inline-flex items-center justify-center rounded-full transition-opacity hover:opacity-100 ${dark ? "text-white/60 hover:text-white" : "text-[#8B9494] hover:text-[#476B6B]"}`}
        aria-label={`Explain: ${data.title}`}
        data-testid={`explainer-trigger-${id}`}
      >
        <Info size={size} strokeWidth={2} />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute z-50 top-5 left-1/2 -translate-x-1/2 w-72 p-3 rounded-md shadow-lg bg-[#1A2424] text-white text-left cursor-default"
          onMouseEnter={() => setOpen(true)}
          onClick={(e) => e.stopPropagation()}
          data-testid={`explainer-popover-${id}`}
        >
          <p className="font-serif text-sm leading-tight mb-2">{data.title}</p>
          <p className="text-[11px] leading-snug text-white/85 mb-2">
            <span className="uppercase tracking-wider text-[9px] text-[#C9A961]">What</span>
            <br />
            {data.what}
          </p>
          {data.math && (
            <p className="text-[11px] leading-snug text-white/85 mb-2 font-mono">
              <span className="uppercase tracking-wider text-[9px] text-[#C9A961] font-sans">
                Calculation
              </span>
              <br />
              {data.math}
            </p>
          )}
          <p className="text-[11px] leading-snug text-white/85">
            <span className="uppercase tracking-wider text-[9px] text-[#C9A961]">
              Why the board cares
            </span>
            <br />
            {data.why}
          </p>
        </span>
      )}
    </span>
  );
}
