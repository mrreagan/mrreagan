/* GlobalSearch — header-mounted command-palette-style search.
 *
 * Trigger: a magnifier icon button in the header. Opens a centered modal
 * with an input field and a live-results dropdown that fans out across
 * workshops, products, partners, research artifacts, and gallery artists.
 *
 * UX choices:
 *   - 250 ms debounce so we don't hammer the backend on every keystroke
 *   - Cmd/Ctrl-K shortcut to open from anywhere
 *   - Esc closes
 *   - Click a result → navigate + close
 *   - Groups results by type with section headings + counts
 *   - Mobile: full-screen overlay
 */
import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import {
  Search, X, GraduationCap, ShoppingBag, Users, FlaskConical, Palette, ArrowRight,
} from "lucide-react";

const TYPE_META = {
  workshop: { label: "Workshops",       Icon: GraduationCap, color: "#476B6B" },
  partner:  { label: "Partners",        Icon: Users,         color: "#9E3C3C" },
  product:  { label: "Shop",            Icon: ShoppingBag,   color: "#C9A961" },
  research: { label: "Research",        Icon: FlaskConical,  color: "#2E5C46" },
  gallery:  { label: "Featured artists", Icon: Palette,      color: "#8B5E3C" },
};
const TYPE_ORDER = ["workshop", "partner", "product", "research", "gallery"];

export default function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Cmd/Ctrl-K → open
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape" && open) setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  // Focus input + lock scroll when modal opens
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      document.body.style.overflow = "";
      // Reset state on close so re-opening doesn't show stale results
      setQ(""); setData(null);
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  // Debounced search
  useEffect(() => {
    if (!open) return;
    if (q.trim().length < 2) { setData(null); return; }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const r = await api.get("/search/global", { params: { q: q.trim(), per_type_limit: 5 } });
        setData(r.data);
      } catch {
        setData({ results: [], counts: {} });
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q, open]);

  const goTo = useCallback((url) => {
    setOpen(false);
    navigate(url);
  }, [navigate]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="p-2 rounded-full hover:bg-[#E5E1D8]/40 transition"
        aria-label="Search"
        title="Search (⌘K)"
        data-testid="global-search-trigger"
      >
        <Search size={20} strokeWidth={1.5} className="text-[#1A2424]" />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm flex items-start justify-center p-4 sm:p-8"
          onClick={() => setOpen(false)}
          data-testid="global-search-modal"
        >
          <div
            className="bg-white w-full max-w-2xl rounded-xl shadow-2xl overflow-hidden mt-[5vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 border-b border-[#E5E1D8] px-4 py-3">
              <Search size={18} strokeWidth={1.5} className="text-[#476B6B] shrink-0" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search workshops, partners, shop, research…"
                className="flex-1 outline-none text-base placeholder-[#5C6B6B]"
                data-testid="global-search-input"
              />
              <kbd className="hidden sm:inline-block text-[10px] px-1.5 py-0.5 border border-[#E5E1D8] rounded text-[#5C6B6B] bg-[#FAF8F5]">esc</kbd>
              <button onClick={() => setOpen(false)} className="text-[#5C6B6B] hover:text-[#1A2424] sm:hidden" aria-label="Close">
                <X size={18} strokeWidth={1.5} />
              </button>
            </div>

            <div className="max-h-[60vh] overflow-y-auto">
              {q.trim().length < 2 && (
                <div className="p-6 text-center text-sm text-[#5C6B6B]" data-testid="search-empty-prompt">
                  Start typing to search across workshops, partners, the shop, research, and featured artists.
                </div>
              )}
              {q.trim().length >= 2 && loading && !data && (
                <p className="p-6 text-sm text-[#5C6B6B]">Searching…</p>
              )}
              {q.trim().length >= 2 && data && (data.results || []).length === 0 && !loading && (
                <p className="p-6 text-sm text-[#5C6B6B] italic" data-testid="search-no-results">
                  Nothing found for "<strong>{q.trim()}</strong>". Try a shorter or different term.
                </p>
              )}
              {data && (data.results || []).length > 0 && (
                <div data-testid="search-results">
                  {TYPE_ORDER.map((t) => {
                    const items = data.results.filter((r) => r.type === t);
                    if (items.length === 0) return null;
                    const meta = TYPE_META[t];
                    const Icon = meta.Icon;
                    return (
                      <section key={t} className="border-b border-[#E5E1D8] last:border-b-0">
                        <div className="px-4 pt-3 pb-1 flex items-center gap-2">
                          <Icon size={12} strokeWidth={1.6} style={{ color: meta.color }} />
                          <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: meta.color }}>
                            {meta.label}
                          </p>
                          <span className="text-[10px] text-[#5C6B6B]">· {items.length}</span>
                        </div>
                        <ul>
                          {items.map((r) => (
                            <li key={`${r.type}-${r.id}`}>
                              <button
                                onClick={() => goTo(r.url)}
                                className="w-full text-left px-4 py-2.5 hover:bg-[#FAF8F5] transition flex items-center gap-3 group"
                                data-testid={`search-result-${r.type}-${r.id}`}
                              >
                                {r.image_url ? (
                                  <img src={r.image_url} alt={r.image_alt || r.title} className="w-10 h-10 rounded object-cover shrink-0 bg-[#FAF8F5]" />
                                ) : (
                                  <div className="w-10 h-10 rounded bg-[#FAF8F5] flex items-center justify-center shrink-0">
                                    <Icon size={14} strokeWidth={1.6} style={{ color: meta.color }} />
                                  </div>
                                )}
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-[#1A2424] truncate">{r.title}</p>
                                  {r.subtitle && (
                                    <p className="text-xs text-[#5C6B6B] truncate">{r.subtitle}</p>
                                  )}
                                </div>
                                <ArrowRight size={14} strokeWidth={1.6} className="text-[#5C6B6B] opacity-0 group-hover:opacity-100 transition" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      </section>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
