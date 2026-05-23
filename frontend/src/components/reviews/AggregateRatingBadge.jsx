import React, { useEffect, useState } from "react";
import api from "../../lib/api";
import { Star } from "lucide-react";

/**
 * Compact aggregate badge — use in product/workshop cards.
 * Renders nothing if there are zero reviews (caller can decide what to show instead).
 */
export default function AggregateRatingBadge({ subjectType, subjectId, size = "sm" }) {
  const [agg, setAgg] = useState(null);
  useEffect(() => {
    api.get(`/reviews/aggregate?subject_type=${subjectType}&subject_id=${subjectId}`)
      .then((r) => setAgg(r.data))
      .catch(() => setAgg(null));
  }, [subjectType, subjectId]);
  if (!agg || agg.count === 0) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 ${size === "sm" ? "text-xs" : "text-sm"} text-[#5C6B6B]`}
      data-testid={`agg-rating-${subjectType}-${subjectId}`}
    >
      <Star size={12} strokeWidth={1.5} fill="#C9A961" className="text-[#C9A961]" />
      <span className="font-medium text-[#1A2424]">{agg.avg.toFixed(1)}</span>
      <span>· {agg.count} review{agg.count === 1 ? "" : "s"}</span>
    </span>
  );
}
