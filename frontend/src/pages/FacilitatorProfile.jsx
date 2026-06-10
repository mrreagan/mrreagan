import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { Star, Calendar } from "lucide-react";
import ShareButton from "../components/ShareButton";
import MessageButton from "../components/MessageButton";

const formatDate = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

export default function FacilitatorProfile() {
  const { slug } = useParams();
  const [f, setF] = useState(null);
  useEffect(() => {
    api.get(`/facilitators/${slug}`).then((r) => setF(r.data)).catch(() => {});
  }, [slug]);

  if (!f) return <div className="container-page py-20" data-testid="facilitator-loading">Loading...</div>;

  return (
    <div className="container-page py-16" data-testid="facilitator-profile-page">
      <Link to="/facilitators" className="text-sm text-[#5C6B6B] hover:text-[#476B6B]">← All facilitators</Link>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 mt-6">
        <div className="lg:col-span-4">
          {f.avatar_url && (
            <div className="card overflow-hidden aspect-[4/5]">
              <img src={f.avatar_url} alt={f.first_name} className="w-full h-full object-cover" />
            </div>
          )}
        </div>
        <div className="lg:col-span-7">
          <span className="label">{f.credentials || "Facilitator"}</span>
          <h1 className="editorial-h1 mt-2">{f.first_name} {f.last_name}</h1>
          {f.avg_rating && (
            <div className="flex items-center gap-2 mt-3">
              <div className="flex">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star key={s} size={16} strokeWidth={1.5} className={s <= Math.round(f.avg_rating) ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"} />
                ))}
              </div>
              <span className="text-sm font-medium">{f.avg_rating}</span>
              <span className="text-xs text-[#5C6B6B]">({f.reviews?.length} reviews)</span>
            </div>
          )}
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            <ShareButton
              surface="facilitator"
              surfaceId={slug}
              path={`/facilitators/${slug}`}
              title={`${f.first_name} ${f.last_name}`}
              emailSubject={`birthright facilitator: ${f.first_name} ${f.last_name}`}
              showLabel
              align="left"
            />
            {f.id && <MessageButton recipientId={f.id} recipientName={`${f.first_name} ${f.last_name}`} />}
          </div>
          <p className="text-base text-[#1A2424] mt-6 leading-relaxed">{f.bio}</p>

          {f.workshops?.length > 0 && (
            <div className="mt-10">
              <span className="label">Workshops</span>
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                {f.workshops.map((w) => (
                  <Link key={w.id} to={`/practice/${w.slug}`} className="card card-hover p-5">
                    <div className="text-xs text-[#5C6B6B] inline-flex items-center gap-1"><Calendar size={11} strokeWidth={1.5} />{formatDate(w.start_date)}</div>
                    <p className="font-serif text-lg mt-1">{w.title}</p>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {f.reviews?.length > 0 && (
            <div className="mt-10">
              <span className="label">From participants</span>
              <div className="mt-4 space-y-4">
                {f.reviews.slice(0, 5).map((r) => (
                  <div key={r.id} className="card p-5">
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((s) => (
                        <Star key={s} size={12} strokeWidth={1.5} className={s <= r.rating ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"} />
                      ))}
                    </div>
                    <p className="text-sm mt-2 text-[#1A2424]">{r.review_text}</p>
                    <p className="text-xs text-[#5C6B6B] mt-2">— {r.user_name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
