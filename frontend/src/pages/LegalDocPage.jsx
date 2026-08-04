import React, { useEffect, useState } from "react";
import { useParams, Link, Navigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft, FileDown } from "lucide-react";
import api from "../lib/api";

// Friendly slugs → route path (must match backend PUBLIC_LEGAL_PAGES keys).
// Kept locally so we can bounce unknown slugs to 404 without a round-trip.
const KNOWN_SLUGS = new Set([
  "terms",
  "privacy",
  "cookie-notice",
  "refunds",
  "scholarships",
  "community-standards",
]);

function formatUpdatedAt(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

export default function LegalDocPage() {
  const { slug } = useParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug || !KNOWN_SLUGS.has(slug)) {
      setError("not-found");
      return;
    }
    setDoc(null);
    setError(null);
    api
      .get(`/legal/pages/${slug}`)
      .then((r) => setDoc(r.data))
      .catch((err) => setError(err.response?.status === 404 ? "not-found" : "error"));
  }, [slug]);

  if (error === "not-found") return <Navigate to="/" replace />;

  if (error) {
    return (
      <div className="container-page py-16" data-testid="legal-doc-error">
        <p className="text-[#9E3C3C]">Failed to load this legal page. Please try again.</p>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="container-page py-16 text-sm text-[#5C6B6B]" data-testid="legal-doc-loading">
        Loading…
      </div>
    );
  }

  const updated = formatUpdatedAt(doc.updated_at);
  const apiBase = process.env.REACT_APP_BACKEND_URL || "";

  return (
    <div className="container-page py-12 max-w-3xl" data-testid={`legal-doc-page-${slug}`}>
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-xs text-[#476B6B] hover:underline"
        data-testid="legal-doc-back"
      >
        <ArrowLeft size={12} strokeWidth={1.5} /> Back to home
      </Link>

      <div className="mt-4">
        <span className="label">Legal · Public</span>
        <h1 className="editorial-h1 mt-2" data-testid="legal-doc-title">
          {doc.title}
        </h1>
        <div className="divider-flame" />
      </div>

      {doc.has_draft_disclaimer && (
        <div
          className="card p-4 bg-[#FFF6E3] border-l-4 border-[#C9A961] mb-6"
          data-testid="legal-doc-draft-banner"
        >
          <p className="text-xs uppercase tracking-wider text-[#7A5A1A] font-bold inline-flex items-center gap-1">
            <AlertTriangle size={12} strokeWidth={2} /> First draft — pending counsel ratification
          </p>
          <p className="text-sm text-[#3D3320] mt-1 leading-relaxed">
            This is a first draft published for transparency and public
            comment. It uses accepted standard language for its type but has
            not yet been ratified by outside counsel. It will be replaced
            with the ratified version — you'll see the banner disappear when
            it does.
          </p>
        </div>
      )}

      {updated && (
        <p className="text-xs text-[#5C6B6B] mb-6" data-testid="legal-doc-updated-at">
          Last updated {updated}
        </p>
      )}

      <article
        className="prose prose-sm sm:prose max-w-none legal-prose"
        // Backend renders the Markdown to HTML server-side; slugs are gated
        // against a hard-coded allowlist in the router so no untrusted input
        // reaches this component.
        dangerouslySetInnerHTML={{ __html: doc.html }}
        data-testid="legal-doc-body"
      />

      <div className="mt-10 pt-6 border-t border-[#E5E1D8] flex flex-wrap gap-3">
        <a
          href={`${apiBase}${doc.docx_url}`}
          className="btn-outline inline-flex items-center gap-2 text-sm"
          data-testid="legal-doc-download-docx"
        >
          <FileDown size={14} strokeWidth={1.6} /> Download .docx
        </a>
        <Link to="/contact" className="btn-ghost inline-flex items-center text-sm">
          Question about this document? Contact us
        </Link>
      </div>
    </div>
  );
}
