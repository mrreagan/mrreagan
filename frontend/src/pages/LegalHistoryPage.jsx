import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { History, BadgeCheck, ArrowLeft } from "lucide-react";
import api from "../lib/api";

// Group ratifications by year so the timeline stays scannable as history
// accumulates. Public docs only (backend filters to the allowlist).
function groupByYear(rows) {
  const out = {};
  for (const r of rows) {
    const y = new Date(r.ratified_at).getUTCFullYear();
    if (!out[y]) out[y] = [];
    out[y].push(r);
  }
  return out;
}

export default function LegalHistoryPage() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get("/legal/history").then((r) => setRows(r.data || [])).catch(() => setError(true));
  }, []);

  const grouped = rows ? groupByYear(rows) : {};
  const years = Object.keys(grouped).sort().reverse();

  return (
    <div className="container-page py-12 max-w-3xl" data-testid="legal-history-page">
      <Link to="/legal" className="inline-flex items-center gap-1 text-xs text-[#476B6B] hover:underline">
        <ArrowLeft size={12} strokeWidth={1.5} /> Back to Legal
      </Link>

      <div className="mt-4">
        <span className="label">Legal · Change log</span>
        <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
          <History size={28} strokeWidth={1.2} /> Ratification history
        </h1>
        <div className="divider-flame" />
      </div>

      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Every time outside counsel ratifies a version of one of our public
        policies, it lands here. Older versions remain part of the record.
      </p>

      {error && (
        <p className="mt-6 text-sm text-[#9E3C3C]" data-testid="legal-history-error">
          Could not load the history. Please refresh.
        </p>
      )}

      {rows && rows.length === 0 && (
        <div className="card p-6 mt-8" data-testid="legal-history-empty">
          <p className="text-sm text-[#5C6B6B]">
            No policies have been ratified yet. When counsel signs off on the
            first draft you&apos;ll see it here.
          </p>
        </div>
      )}

      {rows && rows.length > 0 && (
        <div className="mt-8 space-y-8" data-testid="legal-history-list">
          {years.map((y) => (
            <section key={y} data-testid={`legal-history-year-${y}`}>
              <h2 className="font-serif text-xl text-[#0F2424] mb-3">{y}</h2>
              <ul className="space-y-2">
                {grouped[y].map((r, idx) => (
                  <li
                    key={`${r.slug}-${r.version}-${idx}`}
                    className="card p-4 flex items-start gap-3"
                    data-testid={`legal-history-item-${r.slug}-${r.version}`}
                  >
                    <BadgeCheck size={18} strokeWidth={1.6} className="text-[#2E5C46] mt-1 shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm">
                        <Link to={`/legal/${r.slug}`} className="font-serif text-lg text-[#0F2424] hover:text-[#476B6B] underline decoration-[#E5E1D8]">
                          {r.title}
                        </Link>
                        <span className="text-[#5C6B6B]"> · v{r.version}</span>
                      </p>
                      <p className="text-xs text-[#5C6B6B] mt-0.5">
                        Ratified {new Date(r.ratified_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
                        {r.ratified_by ? ` · ${r.ratified_by}` : ""}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
