import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, Trash2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";

const TYPE_META = {
  workshop:          { label: "Workshops",        link: (id) => `/workshops/${id}` },
  product:           { label: "Shop",             link: (id) => `/shop/${id}` },
  research:          { label: "Research",         link: (id) => `/research#${id}` },
  partner:           { label: "Partners",         link: (id) => `/partners/${id}` },
  facilitator:       { label: "Facilitators",     link: (id) => `/facilitators/${id}` },
  foundation_role:   { label: "Open Roles",       link: (id) => `/join-us/${id}` },
  proposal:          { label: "Proposals",        link: (id) => `/governance/proposals#${id}` },
  impact_statement:  { label: "Impact Stories",   link: () => `/` },
};

const TYPES = Object.keys(TYPE_META);

export default function Bookmarks() {
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/me/bookmarks");
      setBookmarks(data || []);
    } catch {
      toast.error("Could not load bookmarks");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    try {
      await api.delete(`/me/bookmarks/${id}`);
      setBookmarks((b) => b.filter((x) => x.id !== id));
      toast.success("Removed");
    } catch {
      toast.error("Could not remove");
    }
  };

  const filtered = filter === "all" ? bookmarks : bookmarks.filter((b) => b.subject_type === filter);
  const counts = TYPES.reduce((acc, t) => {
    acc[t] = bookmarks.filter((b) => b.subject_type === t).length;
    return acc;
  }, {});

  return (
    <div className="container-page py-12" data-testid="bookmarks-page">
      <span className="label">Dashboard · Saved</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Bookmark size={28} strokeWidth={1.2} /> My Bookmarks
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Anything you save with the bookmark icon across the site lives here — workshops you want to come back to,
        partners worth a second look, research to finish, open roles you're considering.
      </p>

      <div className="flex flex-wrap gap-2 mt-6" data-testid="bookmark-filters">
        <FilterChip active={filter === "all"} onClick={() => setFilter("all")} testid="bookmark-filter-all">
          All ({bookmarks.length})
        </FilterChip>
        {TYPES.map((t) => (
          counts[t] > 0 && (
            <FilterChip key={t} active={filter === t} onClick={() => setFilter(t)} testid={`bookmark-filter-${t}`}>
              {TYPE_META[t].label} ({counts[t]})
            </FilterChip>
          )
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-8">Loading…</p>
      ) : filtered.length === 0 ? (
        <div className="mt-12 text-center py-12 border border-dashed border-[#E5E1D8] rounded">
          <Bookmark size={40} strokeWidth={1} className="mx-auto text-[#C9A961]" />
          <p className="mt-4 text-sm text-[#5C6B6B]">No bookmarks yet. Look for the share/save icon across the site.</p>
        </div>
      ) : (
        <ul className="mt-6 card divide-y divide-[#E5E1D8]" data-testid="bookmark-list">
          {filtered.map((b) => {
            const meta = TYPE_META[b.subject_type] || {};
            const href = meta.link ? meta.link(b.subject_id) : null;
            return (
              <li key={b.id} className="py-4 px-4 flex items-center gap-3" data-testid={`bookmark-row-${b.id}`}>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">{meta.label || b.subject_type}</p>
                  <p className="font-medium truncate">{b.label || b.subject_id}</p>
                  {b.note && <p className="text-xs text-[#5C6B6B] mt-1">{b.note}</p>}
                  <p className="text-[10px] text-[#5C6B6B] mt-1">Saved {new Date(b.created_at).toLocaleDateString()}</p>
                </div>
                {href && (
                  <Link to={href} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`bookmark-open-${b.id}`}>
                    Open <ExternalLink size={12} strokeWidth={1.5} />
                  </Link>
                )}
                <button onClick={() => remove(b.id)} className="text-[#5C6B6B] hover:text-red-600 p-2" aria-label="Remove" data-testid={`bookmark-remove-${b.id}`}>
                  <Trash2 size={14} strokeWidth={1.5} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, children, testid }) {
  return (
    <button
      onClick={onClick}
      data-testid={testid}
      className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
        active ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
      }`}
    >
      {children}
    </button>
  );
}
