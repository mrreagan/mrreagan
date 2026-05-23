import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Star, ShieldCheck, Search, Filter } from "lucide-react";

const CATEGORY_CHIPS = [
  { id: "all", label: "All" },
  { id: "workshop", label: "Workshops" },
  { id: "apparel", label: "Apparel" },
  { id: "journals", label: "Journals" },
  { id: "books", label: "Books" },
  { id: "prints", label: "Prints" },
  { id: "stickers", label: "Stickers" },
  { id: "decks", label: "Decks" },
  { id: "home", label: "Home & lifestyle" },
  { id: "bags", label: "Bags & accessories" },
];

const STAR_FILTERS = [0, 5, 4, 3];

function ReviewCard({ review }) {
  const detailHref = review.subject_type === "workshop"
    ? `/workshops/${review.subject_id}`
    : `/shop/${review.subject_id}`;
  return (
    <div className="card p-5" data-testid={`xs-review-${review.id}`}>
      <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">
        {review.subject_type === "workshop" ? "Workshop" : (review.subject_category || "Product")}
      </p>
      <Link to={detailHref} className="font-serif text-lg block mt-1 hover:text-[#476B6B]">
        {review.subject_label}
      </Link>
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="inline-flex">
          {[1, 2, 3, 4, 5].map((s) => (
            <Star key={s} size={13} strokeWidth={1.5} fill={s <= review.rating ? "#C9A961" : "transparent"} className={s <= review.rating ? "text-[#C9A961]" : "text-[#E5E1D8]"} />
          ))}
        </span>
        <span className="text-xs text-[#1A2424]">— {review.user_name}</span>
        {review.verified_purchase && (
          <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#2E5C46]">
            <ShieldCheck size={10} strokeWidth={2} /> Verified
          </span>
        )}
      </div>
      <p className="text-sm mt-3 line-clamp-4 whitespace-pre-wrap">{review.review_text}</p>
    </div>
  );
}

export default function ReviewsBrowser() {
  const [category, setCategory] = useState("all");
  const [minRating, setMinRating] = useState(0);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (category && category !== "all") params.set("subject_category", category);
    if (minRating) params.set("min_rating", minRating);
    if (q.trim().length >= 2) params.set("q", q.trim());
    params.set("limit", "100");
    setLoading(true);
    const t = setTimeout(() => {
      api.get(`/reviews/search?${params}`)
        .then((r) => setResults(r.data))
        .finally(() => setLoading(false));
    }, 300); // debounce
    return () => clearTimeout(t);
  }, [category, minRating, q]);

  return (
    <div className="container-page py-12" data-testid="reviews-browser-page">
      <span className="label">Trust ecosystem</span>
      <h1 className="editorial-h1 mt-2">What people say</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-xl">
        Every transactional offering on Birthright has reviews from real participants and buyers. Browse, compare, decide.
      </p>

      <div className="mt-8 space-y-4">
        <div className="relative">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search reviews (e.g. 'fit', 'kind', 'transformed')"
            className="input-field pl-9"
            data-testid="reviews-search-q"
          />
        </div>

        <div className="flex flex-wrap gap-2" data-testid="reviews-category-filters">
          {CATEGORY_CHIPS.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                category === c.id ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`reviews-cat-${c.id}`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B] inline-flex items-center gap-1">
            <Filter size={11} strokeWidth={1.5} /> Min rating
          </span>
          {STAR_FILTERS.map((n) => (
            <button
              key={n}
              onClick={() => setMinRating(n)}
              className={`px-3 py-1 rounded-full text-xs border transition ${
                minRating === n ? "bg-[#C9A961]/15 text-[#C9A961] border-[#C9A961]" : "bg-white text-[#1A2424] border-[#E5E1D8]"
              }`}
              data-testid={`reviews-stars-${n}`}
            >
              {n === 0 ? "Any" : `${n}★ +`}
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-[#5C6B6B] mt-6">
        {loading ? "Searching…" : `${results.length} review${results.length === 1 ? "" : "s"} matching`}
      </p>

      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="reviews-results">
        {results.map((r) => <ReviewCard key={r.id} review={r} />)}
        {!loading && results.length === 0 && (
          <div className="col-span-full card p-12 text-center">
            <Star size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
            <p className="font-serif text-lg mt-3">No reviews yet match.</p>
            <p className="text-sm text-[#5C6B6B] mt-1">Try a broader category or lower the minimum rating.</p>
          </div>
        )}
      </div>
    </div>
  );
}
