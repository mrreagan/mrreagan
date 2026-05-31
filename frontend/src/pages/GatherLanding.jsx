import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronRight, MapPin, Users, Search, Plus, ArrowLeft } from "lucide-react";
import api from "../lib/api";

const KIND_BADGE = {
  continent: "bg-[#F4F1EA] text-[#5C6B6B]",
  country: "bg-[#FFF8E1] text-[#8B7128]",
  region: "bg-[#E8F4EC] text-[#476B6B]",
  city: "bg-[#F2EBE0] text-[#9E6C2C]",
  neighborhood: "bg-[#F4EFE5] text-[#5C6B6B]",
};

export default function GatherLanding() {
  const [params] = useSearchParams();
  const parent = params.get("under") || null;
  const [nodes, setNodes] = useState([]);
  const [parentNode, setParentNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/gather/tree", { params: parent ? { parent_slug: parent } : {} }),
      parent ? api.get(`/gather/community/${parent}`).catch(() => ({ data: null })) : Promise.resolve({ data: null }),
    ]).then(([t, p]) => {
      setNodes(t.data || []);
      setParentNode(p.data?.community || null);
    }).finally(() => setLoading(false));
  }, [parent]);

  const onSearch = async (e) => {
    e.preventDefault();
    if (q.trim().length < 2) return setResults([]);
    const r = await api.get("/gather/search", { params: { q: q.trim() } });
    setResults(r.data || []);
  };

  return (
    <div className="container-page py-12" data-testid="gather-landing">
      <span className="label">Gather</span>
      <h1 className="editorial-h1 mt-2">
        {parentNode ? parentNode.label : "Communities of practice"}
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        {parent
          ? "Drill down to your city, or read what's happening here."
          : "Find people doing the work near you. Browse the world by continent, then country, then closer in."}
      </p>

      {!parent && (
        <form onSubmit={onSearch} className="mt-6 flex gap-2 max-w-xl" data-testid="gather-search-form">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search communities…" className="input-field flex-1" data-testid="gather-search-input" />
          <button type="submit" className="btn-outline inline-flex items-center gap-1" data-testid="gather-search-btn">
            <Search size={14} strokeWidth={1.8} /> Search
          </button>
        </form>
      )}

      {results.length > 0 && (
        <div className="mt-3 max-w-xl space-y-1" data-testid="gather-search-results">
          {results.map((r) => (
            <Link key={r.slug} to={`/gather/community/${r.slug}`} className="block px-3 py-2 rounded hover:bg-[#F4F1EA] text-sm" data-testid={`gather-result-${r.slug}`}>
              <span className="font-medium">{r.label}</span>
              <span className="text-[#5C6B6B] text-xs ml-2">· {r.kind} · {r.parent_slug || "—"}</span>
            </Link>
          ))}
        </div>
      )}

      {parent && (
        <div className="mt-4 text-sm">
          <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-[#476B6B] hover:text-[#0F2424]" data-testid="gather-back-btn">
            <ArrowLeft size={14} strokeWidth={1.6} /> back
          </button>
          {parentNode && (
            <Link to={`/gather/community/${parent}`} className="btn-outline text-xs ml-3" data-testid="gather-visit-here">
              Visit {parentNode.label} community →
            </Link>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-8">Loading…</p>
      ) : nodes.length === 0 ? (
        <div className="card p-6 mt-6 max-w-xl text-center" data-testid="gather-empty">
          <p className="text-base text-[#5C6B6B]">
            No sub-communities here yet. Don't see your city or neighborhood?
          </p>
          {parent && (
            <Link to={`/gather/propose?under=${encodeURIComponent(parent)}`} className="btn-primary text-sm mt-3 inline-flex items-center gap-2" data-testid="gather-propose-cta">
              <Plus size={14} /> Propose a community here
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-6" data-testid="gather-tree-grid">
          {nodes.map((n) => (
            <Link key={n.slug} to={`/gather?under=${encodeURIComponent(n.slug)}`} className="card p-4 hover:shadow-md transition flex items-center justify-between" data-testid={`gather-node-${n.slug}`}>
              <div>
                <p className="font-serif text-lg leading-tight">{n.label}</p>
                <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-1 inline-flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded-full ${KIND_BADGE[n.kind] || "bg-[#F4F1EA]"}`}>{n.kind}</span>
                  {n.member_count > 0 && (
                    <span className="inline-flex items-center gap-0.5"><Users size={10} strokeWidth={1.8} /> {n.member_count}</span>
                  )}
                </p>
              </div>
              <ChevronRight size={16} strokeWidth={1.5} className="text-[#476B6B]" />
            </Link>
          ))}
          {parent && (
            <Link to={`/gather/propose?under=${encodeURIComponent(parent)}`} className="card p-4 hover:shadow-md transition border-dashed inline-flex items-center justify-center gap-2 text-[#476B6B]" data-testid="gather-propose-tile">
              <Plus size={16} /> Propose a community here
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
