import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { Calendar, Users, ArrowRight, Search, Star } from "lucide-react";
import ShareButton from "../components/ShareButton";

const formatDate = (iso) => {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

const statusBadge = (status) => {
  const styles = {
    upcoming: "bg-[#476B6B] text-white",
    in_progress: "bg-[#C9A961] text-white",
    completed: "bg-[#E5E1D8] text-[#5C6B6B]",
    cancelled: "bg-[#9E3C3C] text-white",
  };
  const labels = { upcoming: "Upcoming", in_progress: "In Progress", completed: "Completed", cancelled: "Cancelled" };
  return <span className={`text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full font-medium ${styles[status] || styles.upcoming}`}>{labels[status] || status}</span>;
};

export default function Workshops() {
  const [workshops, setWorkshops] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("upcoming");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filter !== "all") params.append("status", filter);
    if (search) params.append("search", search);
    api
      .get(`/workshops?${params}`)
      .then((r) => setWorkshops(r.data))
      .finally(() => setLoading(false));
  }, [search, filter]);

  return (
    <div className="container-page py-16" data-testid="workshops-page">
      <div className="max-w-2xl">
        <span className="label">Workshops</span>
        <h1 className="editorial-h1 mt-3">Find your next practice.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Browse our upcoming workshops. Each one is a small container with a defined arc, held in person by trained facilitators.
        </p>
      </div>

      <div className="mt-10 flex flex-col md:flex-row gap-3 md:items-center" data-testid="workshops-filters">
        <div className="flex items-center gap-2 input-field md:max-w-sm">
          <Search size={16} strokeWidth={1.5} className="text-[#5C6B6B] shrink-0" />
          <input
            placeholder="Search workshops"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent outline-none flex-1 text-sm"
            data-testid="workshops-search"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {["upcoming", "in_progress", "completed", "all"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
                filter === f ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`filter-${f}`}
            >
              {f === "all" ? "All" : f === "in_progress" ? "In Progress" : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-12">Loading...</p>
      ) : workshops.length === 0 ? (
        <p className="text-sm text-[#5C6B6B] mt-12" data-testid="workshops-empty">No workshops match your search.</p>
      ) : (
        <div className="mt-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="workshops-list">
          {workshops.map((w) => <WorkshopCard key={w.id} w={w} />)}
        </div>
      )}
    </div>
  );
}

function WorkshopCard({ w }) {
  const navigate = useNavigate();
  const go = () => navigate(`/workshops/${w.slug}`);
  return (
    <div
      role="link"
      tabIndex={0}
      onClick={go}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") go(); }}
      className="card card-hover overflow-hidden block cursor-pointer"
      data-testid={`workshop-card-${w.slug}`}
    >
      <div className="aspect-[4/3] bg-[#E5E1D8] relative overflow-hidden">
        <img src={w.image_url} alt={w.title} className="w-full h-full object-cover" />
        <div className="absolute top-4 left-4">{statusBadge(w.status)}</div>
      </div>
      <div className="p-6">
        <div className="flex items-center gap-3 text-xs text-[#5C6B6B] mb-2">
          <span className="inline-flex items-center gap-1"><Calendar size={12} strokeWidth={1.5} />{formatDate(w.start_date)}</span>
          {w.status === "upcoming" && (
            <span className="inline-flex items-center gap-1"><Users size={12} strokeWidth={1.5} />{w.spots_left} of {w.capacity}</span>
          )}
        </div>
        <h3 className="font-serif text-2xl mb-2 leading-tight">{w.title}</h3>
        <p className="text-sm text-[#5C6B6B] line-clamp-3">{w.short_description}</p>
        <div className="mt-5 pt-4 border-t border-[#E5E1D8] flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-[#476B6B]">
            {w.status === "upcoming" ? `From $${w.early_bird_price?.toFixed(0)}` : `$${w.regular_price?.toFixed(0)}`}
          </span>
          <div className="flex items-center gap-2">
            <ShareButton
              surface="workshop"
              surfaceId={w.id}
              path={`/workshops/${w.slug}`}
              title={w.title}
              emailSubject={`Workshop: ${w.title}`}
              size="sm"
              stopPropagation
            />
            <ArrowRight size={16} strokeWidth={1.5} className="text-[#C9A961]" />
          </div>
        </div>
      </div>
    </div>
  );
}
