import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, ChevronRight, Scale } from "lucide-react";
import api from "../lib/api";

// One-line preview per public doc — kept locally so the index reads
// cleanly even before the API returns. Slugs match the backend
// PUBLIC_LEGAL_PAGES allowlist in routers/legal.py.
const PREVIEWS = {
  terms: "How buying, joining, and partnering works — plus warranty and liability.",
  privacy: "What we collect, why, who we share it with, and how to reach us.",
  "cookie-notice": "Which cookies we use and how to change your consent.",
  refunds: "Returns, workshop cancellations, and how to request a refund.",
  scholarships: "How sliding-scale pricing and full scholarships work.",
  "community-standards": "How we keep this space attentive, honest, and safe.",
};

export default function LegalIndex() {
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .get("/legal/pages")
      .then((r) => setDocs(r.data || []))
      .catch(() => setError(true));
  }, []);

  return (
    <div className="container-page py-12 max-w-3xl" data-testid="legal-index-page">
      <span className="label">Legal · Public</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Scale size={28} strokeWidth={1.2} /> Legal
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Every public policy we operate under. Each page is a first draft
        pending counsel ratification &mdash; you&apos;ll see the banner
        disappear when it&apos;s ratified.
      </p>

      {error && (
        <p className="mt-6 text-sm text-[#9E3C3C]" data-testid="legal-index-error">
          Could not load the index. Please refresh.
        </p>
      )}

      {docs && (
        <ul className="mt-8 space-y-3" data-testid="legal-index-list">
          {docs.map((d) => (
            <li key={d.slug}>
              <Link
                to={`/legal/${d.slug}`}
                className="card p-5 flex items-start gap-4 hover:border-[#476B6B] transition"
                data-testid={`legal-index-item-${d.slug}`}
              >
                <FileText size={20} strokeWidth={1.4} className="text-[#476B6B] shrink-0 mt-1" />
                <div className="flex-1">
                  <p className="font-serif text-lg text-[#0F2424]">{d.title}</p>
                  {PREVIEWS[d.slug] && (
                    <p className="text-sm text-[#5C6B6B] mt-1 leading-relaxed">
                      {PREVIEWS[d.slug]}
                    </p>
                  )}
                </div>
                <ChevronRight size={16} strokeWidth={1.5} className="text-[#5C6B6B] mt-2 shrink-0" />
              </Link>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-10 pt-6 border-t border-[#E5E1D8] text-xs text-[#5C6B6B] flex flex-wrap items-center gap-3">
        <Link to="/legal/history" className="underline text-[#476B6B] hover:text-[#0F2424]" data-testid="legal-index-history-link">
          Ratification history →
        </Link>
        <span>·</span>
        <span>
          Questions?{" "}
          <a href="mailto:legal@birthright.live" className="underline text-[#476B6B]">
            legal@birthright.live
          </a>
        </span>
      </div>
    </div>
  );
}
