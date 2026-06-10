import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { BookOpen, Users, Infinity as InfinityIcon, ArrowRight, Sparkles, Calendar, Search } from "lucide-react";
import ShareButton from "../components/ShareButton";

const TIERS = [
  {
    key: "foundations",
    num: "01",
    icon: BookOpen,
    title: "Foundations",
    subtitle: "On-ramp immersions",
    body:
      "Open to anyone. No prerequisites. Where the practice begins — research-backed conversations and skills you can apply the same week.",
  },
  {
    key: "practice",
    num: "02",
    icon: Users,
    title: "Practice",
    subtitle: "Skill labs for graduates",
    body:
      "For those continuing the work. Pair-practice, supervised reps, and targeted exercises with certified facilitators.",
  },
  {
    key: "living_the_work",
    num: "03",
    icon: InfinityIcon,
    title: "Living the Work",
    subtitle: "Community circles",
    body:
      "An ongoing peer container for alumni. Keep the practice alive between formal trainings. Optional, ongoing.",
  },
];

// Editorial teaser the user previewed in chat — surfaced until the workshop is
// actually published via the admin UI.
const FOUNDATION_TEASER = {
  tier: "foundations",
  title: "Seven Conversations in a Day",
  body:
    "A one-day couples workshop guiding partners through seven research-backed conversations — distilled into a self-supporting, efficient format. Innovative, AI-assisted prompts and structured supports help couples move quickly and successfully through the work in a single day.",
};

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
  const labels = { upcoming: "Upcoming", in_progress: "In progress", completed: "Completed", cancelled: "Cancelled" };
  return (
    <span className={`text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full font-medium ${styles[status] || styles.upcoming}`}>
      {labels[status] || status}
    </span>
  );
};

export default function Experiences() {
  const [workshops, setWorkshops] = useState([]);
  const [content, setContent] = useState(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("upcoming");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/foundation/content").then((r) => setContent(r.data)).catch(() => {});
  }, []);

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

  const foundationByTier = useMemo(() => {
    const map = { foundations: [], practice: [], living_the_work: [] };
    for (const w of workshops) {
      if (w.is_foundation && w.track && map[w.track]) {
        map[w.track].push(w);
      }
    }
    return map;
  }, [workshops]);

  const otherWorkshops = useMemo(
    () => workshops.filter((w) => !w.is_foundation),
    [workshops]
  );

  return (
    <div className="container-page py-16" data-testid="experiences-page">
      {/* ---------- Hero ---------- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 mb-16">
        <div className="lg:col-span-6">
          <span className="label">Workshop</span>
          <h1 className="editorial-h1 mt-3">A practice, not a curriculum.</h1>
          <div className="divider-flame" />
          <p className="text-base text-[#1A2424] leading-relaxed">
            {content?.education_structure ||
              "birthright is a lifelong relational practice. Our Foundation library leads the way — original IP designed by the foundation — surrounded by complementary workshops from our facilitators and partner community."}
          </p>
          <p className="text-sm text-[#5C6B6B] leading-relaxed mt-4">
            Browse the Foundation library by tier below, or scroll to all other workshops in our community.
          </p>
        </div>
        <div className="lg:col-span-5 lg:col-start-8 self-start">
          <div className="card p-6 bg-[#FAF8F5]" data-testid="experiences-hero-card">
            <div className="inline-flex items-center gap-2 text-[#C9A961]">
              <Sparkles size={14} strokeWidth={1.5} />
              <span className="label !mt-0">Foundation IP</span>
            </div>
            <h3 className="font-serif text-2xl mt-3 leading-tight">
              The Foundation library is our original work.
            </h3>
            <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">
              Three tiers — <em>Foundations</em>, <em>Practice</em>, and <em>Living the Work</em> — form a single
              learning arc designed by the foundation. Other workshops in the community build alongside this
              spine.
            </p>
          </div>
        </div>
      </div>

      {/* ---------- Foundation Library: three tiers ---------- */}
      <section data-testid="experiences-foundation-section" className="mb-20">
        <div className="flex items-end justify-between flex-wrap gap-3 mb-6">
          <div>
            <span className="label">01 / Foundation library</span>
            <h2 className="font-serif text-3xl md:text-4xl mt-2 leading-tight">The three-tier framework.</h2>
          </div>
          <p className="text-xs text-[#5C6B6B] max-w-sm">
            Designed as a progression. Most people start at Foundations and stay involved in Living the Work indefinitely.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="experiences-tiers">
          {TIERS.map((t) => {
            const tierWorkshops = foundationByTier[t.key] || [];
            const showTeaser = t.key === "foundations" && tierWorkshops.length === 0;
            return (
              <div
                key={t.key}
                className="card p-7 flex flex-col"
                data-testid={`tier-${t.key}`}
              >
                <div className="flex items-baseline justify-between">
                  <span className="label">{t.num}</span>
                  <span className="text-[11px] text-[#5C6B6B]">{t.subtitle}</span>
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <div className="shrink-0 w-12 h-12 rounded-full border border-[#E5E1D8] flex items-center justify-center text-[#C9A961]">
                    <t.icon size={20} strokeWidth={1.5} />
                  </div>
                  <h3 className="font-serif text-2xl">{t.title}</h3>
                </div>
                <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{t.body}</p>

                <div className="mt-5 pt-5 border-t border-[#E5E1D8] flex-1 flex flex-col gap-3">
                  <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                    Foundation workshops in this tier
                  </p>
                  {tierWorkshops.length > 0 ? (
                    tierWorkshops.map((w) => (
                      <TierWorkshopRow key={w.id} w={w} />
                    ))
                  ) : showTeaser ? (
                    <div
                      className="rounded-lg border border-dashed border-[#C9A961] bg-[#FFF8E1] p-4"
                      data-testid="tier-foundations-teaser"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-[#8B7128]">In development</p>
                      <h4 className="font-serif text-lg mt-1">{FOUNDATION_TEASER.title}</h4>
                      <p className="text-xs text-[#5C6B6B] mt-2 leading-relaxed">
                        {FOUNDATION_TEASER.body}
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-[#5C6B6B] italic">
                      Foundation material for this tier is in development. Check back soon.
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ---------- Other workshops bucket ---------- */}
      <section data-testid="experiences-other-section">
        <div className="flex items-end justify-between flex-wrap gap-3 mb-6">
          <div>
            <span className="label">02 / Community workshops</span>
            <h2 className="font-serif text-3xl md:text-4xl mt-2 leading-tight">All other workshops.</h2>
            <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
              Offerings from our facilitators and partner community. These build alongside the Foundation library.
            </p>
          </div>
        </div>

        <div className="mt-2 flex flex-col md:flex-row gap-3 md:items-center" data-testid="experiences-other-filters">
          <div className="flex items-center gap-2 input-field md:max-w-sm">
            <Search size={16} strokeWidth={1.5} className="text-[#5C6B6B] shrink-0" />
            <input
              placeholder="Search workshops"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent outline-none flex-1 text-sm"
              data-testid="experiences-search"
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
                data-testid={`experiences-filter-${f}`}
              >
                {f === "all" ? "All" : f === "in_progress" ? "In progress" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-[#5C6B6B] mt-12">Loading...</p>
        ) : otherWorkshops.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-12" data-testid="experiences-other-empty">
            No community workshops match your search.
          </p>
        ) : (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="experiences-other-list">
            {otherWorkshops.map((w) => (
              <WorkshopCard key={w.id} w={w} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function TierWorkshopRow({ w }) {
  return (
    <Link
      to={`/practice/${w.slug}`}
      className="group flex items-start gap-3 rounded-lg border border-[#E5E1D8] p-3 hover:border-[#476B6B] transition"
      data-testid={`tier-workshop-${w.slug}`}
    >
      <div className="w-14 h-14 rounded bg-[#E5E1D8] overflow-hidden shrink-0">
        {w.image_url && <img src={w.image_url} alt={w.title} className="w-full h-full object-cover" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-serif text-base leading-tight truncate">{w.title}</p>
        <p className="text-[11px] text-[#5C6B6B] mt-1 inline-flex items-center gap-1">
          <Calendar size={11} strokeWidth={1.5} /> {formatDate(w.start_date)}
        </p>
      </div>
      <ArrowRight size={14} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0 group-hover:translate-x-0.5 transition-transform" />
    </Link>
  );
}

function WorkshopCard({ w }) {
  const navigate = useNavigate();
  const go = () => navigate(`/practice/${w.slug}`);
  return (
    <div
      role="link"
      tabIndex={0}
      onClick={go}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") go(); }}
      className="card card-hover overflow-hidden block cursor-pointer"
      data-testid={`experiences-card-${w.slug}`}
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
              path={`/practice/${w.slug}`}
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
