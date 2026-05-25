import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Microscope, BookOpen, Sparkles, ExternalLink as LinkIcon, Search, Clock } from "lucide-react";

export default function Research() {
  const [artifacts, setArtifacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    setLoading(true);
    const url = q.trim().length >= 2 ? `/research?q=${encodeURIComponent(q.trim())}` : "/research";
    api.get(url)
      .then((r) => setArtifacts(r.data))
      .finally(() => setLoading(false));
  }, [q]);

  const now = new Date().toISOString();
  const promoted = artifacts.filter((a) => a.promoted_until && a.promoted_until > now);
  const others = artifacts.filter((a) => !a.promoted_until || a.promoted_until <= now);

  return (
    <div className="container-page py-12" data-testid="research-page">
      <span className="label">Research</span>
      <h1 className="editorial-h1 mt-2">Birthright Research Library</h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Peer-reviewed papers, practitioner briefs, and field reports from our research partners on attachment, relational repair, and family systems.
      </p>

      <div className="mt-6 max-w-md relative">
        <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search title, authors, abstract..."
          className="input-field pl-9 text-sm w-full"
          data-testid="research-search"
        />
      </div>

      {loading && <p className="text-sm text-[#5C6B6B] mt-8">Loading research...</p>}

      {!loading && promoted.length > 0 && (
        <section className="mt-10" data-testid="research-promoted-section">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} strokeWidth={1.5} className="text-[#C9A961]" />
            <h2 className="font-serif text-2xl">Promoted this month</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {promoted.map((a) => <ArtifactCard key={a.id} artifact={a} highlight />)}
          </div>
        </section>
      )}

      {!loading && (
        <section className="mt-10" data-testid="research-listing">
          <h2 className="font-serif text-2xl mb-3">All research</h2>
          {others.length === 0 && promoted.length === 0 && (
            <div className="card p-10 text-center text-sm text-[#5C6B6B]">No artifacts yet.</div>
          )}
          <div className="grid md:grid-cols-2 gap-4">
            {others.map((a) => <ArtifactCard key={a.id} artifact={a} />)}
          </div>
        </section>
      )}
    </div>
  );
}

function ArtifactCard({ artifact, highlight }) {
  const TierIcon = artifact.tier === "paper" ? BookOpen : Microscope;
  const tierLabel = artifact.tier === "paper" ? "Peer-reviewed paper" : "Practitioner brief";
  return (
    <article
      className={`card p-5 hover:border-[#476B6B] transition relative ${highlight ? "ring-2 ring-[#C9A961]" : ""}`}
      data-testid={`research-card-${artifact.id}`}
    >
      {highlight && (
        <span className="absolute top-3 right-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424]">
          <Sparkles size={9} strokeWidth={2} /> Promoted
        </span>
      )}
      {artifact.cover_image_url && (
        <img src={artifact.cover_image_url} alt="" className="w-full h-32 object-cover rounded mb-4" />
      )}
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-[#476B6B]">
        <TierIcon size={11} strokeWidth={1.5} />
        <span>{tierLabel}</span>
        {artifact.estimated_read_minutes && (
          <>
            <span>·</span>
            <span className="inline-flex items-center gap-1"><Clock size={10} strokeWidth={1.5} /> {artifact.estimated_read_minutes} min</span>
          </>
        )}
      </div>
      <h3 className="font-serif text-xl mt-2" data-testid={`research-title-${artifact.id}`}>{artifact.title}</h3>
      <p className="text-xs text-[#5C6B6B] mt-1">
        {artifact.authors} ·{" "}
        <Link to={`/partners/${artifact.partner_slug}`} className="hover:underline text-[#476B6B]">{artifact.partner_display_name}</Link>
        {" · "}{new Date(artifact.publication_date).toLocaleDateString()}
      </p>
      <p className="text-sm text-[#1A2424] mt-3 leading-relaxed line-clamp-4">{artifact.abstract}</p>
      {Array.isArray(artifact.tags) && artifact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {artifact.tags.slice(0, 4).map((t) => (
            <span key={t} className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#F4F1EA] text-[#5C6B6B]">{t}</span>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#E5E1D8]">
        {artifact.doi && <span className="text-[10px] text-[#5C6B6B] font-mono">DOI: {artifact.doi}</span>}
        <a
          href={artifact.full_text_url}
          target="_blank"
          rel="noreferrer noopener"
          className="text-sm text-[#476B6B] hover:underline inline-flex items-center gap-1 ml-auto"
          data-testid={`research-link-${artifact.id}`}
        >
          Read full text <LinkIcon size={12} strokeWidth={1.5} />
        </a>
      </div>
    </article>
  );
}
