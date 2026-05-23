import React, { useEffect, useMemo, useState } from "react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { Star, ShieldCheck, Flag, EyeOff, Pencil } from "lucide-react";

function StarRow({ value, onChange, readOnly = false, size = 16 }) {
  return (
    <div className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => !readOnly && onChange?.(n)}
          disabled={readOnly}
          className={readOnly ? "" : "cursor-pointer"}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
        >
          <Star
            size={size}
            strokeWidth={1.5}
            fill={n <= value ? "#C9A961" : "transparent"}
            className={n <= value ? "text-[#C9A961]" : "text-[#5C6B6B]"}
          />
        </button>
      ))}
    </div>
  );
}

/**
 * Compact aggregate badge — use in product/workshop cards.
 * Renders nothing if there are zero reviews (caller can decide to show "Not yet reviewed").
 */
export function AggregateRatingBadge({ subjectType, subjectId, size = "sm" }) {
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

function ReviewItem({ review, currentUserId, isAdmin, onReport, onModerate }) {
  const [showReport, setShowReport] = useState(false);
  const [reason, setReason] = useState("");
  return (
    <div className={`border-b border-[#E5E1D8] py-4 last:border-0 ${review.moderated ? "opacity-50" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <StarRow value={review.rating} readOnly size={14} />
            <span className="text-sm font-medium">{review.user_name}</span>
            {review.verified_purchase && (
              <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#2E5C46]" title="Verified purchaser">
                <ShieldCheck size={11} strokeWidth={2} /> Verified
              </span>
            )}
            <span className="text-[10px] text-[#5C6B6B]">{new Date(review.created_at).toLocaleDateString()}</span>
          </div>
          {review.moderated ? (
            <p className="text-xs italic text-[#B86A5C] mt-2">
              <EyeOff size={11} strokeWidth={1.5} className="inline mr-1" />
              This review was hidden by moderation{review.moderation_reason ? `: ${review.moderation_reason}` : ""}.
            </p>
          ) : (
            <p className="text-sm mt-2 whitespace-pre-wrap">{review.review_text}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          {currentUserId && currentUserId !== review.user_id && !review.moderated && !showReport && (
            <button onClick={() => setShowReport(true)} className="text-[10px] text-[#5C6B6B] hover:text-[#B86A5C] inline-flex items-center gap-1" data-testid={`report-review-${review.id}`}>
              <Flag size={10} strokeWidth={1.5} /> Report
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => onModerate(review)}
              className="text-[10px] text-[#5C6B6B] hover:text-[#B86A5C] inline-flex items-center gap-1"
              data-testid={`moderate-review-${review.id}`}
            >
              <EyeOff size={10} strokeWidth={1.5} /> {review.moderated ? "Restore" : "Hide"}
            </button>
          )}
        </div>
      </div>
      {showReport && (
        <div className="mt-3 flex gap-2" data-testid={`report-form-${review.id}`}>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why is this inappropriate?"
            className="input-field text-xs"
            maxLength={500}
          />
          <button onClick={() => { onReport(review, reason); setShowReport(false); setReason(""); }} className="btn-outline text-xs">Send</button>
          <button onClick={() => { setShowReport(false); setReason(""); }} className="btn-outline text-xs">Cancel</button>
        </div>
      )}
    </div>
  );
}

/**
 * <ReviewSection /> — full review block: list + write/edit form + aggregate.
 *
 * Use anywhere: workshop hubs, product details, future services.
 */
export default function ReviewSection({ subjectType, subjectId, subjectLabel }) {
  const { user } = useAuth();
  const isAuthenticated = !!user;
  const [reviews, setReviews] = useState([]);
  const [agg, setAgg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [anonymous, setAnonymous] = useState(false);

  const myReview = useMemo(
    () => (user ? reviews.find((r) => r.user_id === user.id) : null),
    [reviews, user]
  );

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get(`/reviews?subject_type=${subjectType}&subject_id=${subjectId}`),
      api.get(`/reviews/aggregate?subject_type=${subjectType}&subject_id=${subjectId}`),
    ])
      .then(([rRes, aRes]) => { setReviews(rRes.data); setAgg(aRes.data); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [subjectType, subjectId]);

  useEffect(() => {
    if (myReview && editing) {
      setRating(myReview.rating);
      setText(myReview.review_text);
      setAnonymous(myReview.anonymous);
    }
  }, [myReview, editing]);

  const submit = async (e) => {
    e.preventDefault();
    if (text.trim().length < 10) {
      toast.error("Please write at least 10 characters.");
      return;
    }
    try {
      await api.post("/reviews", {
        subject_type: subjectType, subject_id: subjectId,
        rating, review_text: text, anonymous,
      });
      toast.success(myReview ? "Review updated" : "Thanks for your review");
      setEditing(false); setText(""); setRating(5); setAnonymous(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit review");
    }
  };

  const report = async (review, reason) => {
    if (!reason.trim()) { toast.error("Please add a brief reason"); return; }
    try {
      await api.post(`/reviews/${review.id}/report`, { reason });
      toast.success("Report sent for review");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not report");
    }
  };

  const moderate = async (review) => {
    try {
      await api.post(`/reviews/${review.id}/moderate`, {
        moderated: !review.moderated,
        reason: review.moderated ? null : "Hidden by moderator",
      });
      load();
    } catch (err) {
      toast.error("Moderation failed");
    }
  };

  const isAdmin = user?.role === "admin" || user?.role === "ombudsman";
  const canShowForm = isAuthenticated && (editing || !myReview);

  return (
    <div className="card p-6" data-testid="review-section">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <span className="label">Reviews</span>
          <h3 className="font-serif text-2xl mt-1">{subjectLabel || "What people are saying"}</h3>
        </div>
        {agg && agg.count > 0 && (
          <div className="text-right">
            <div className="flex items-center gap-2">
              <StarRow value={Math.round(agg.avg)} readOnly />
              <span className="font-serif text-2xl">{agg.avg.toFixed(1)}</span>
            </div>
            <p className="text-xs text-[#5C6B6B] mt-1">
              {agg.count} review{agg.count === 1 ? "" : "s"}
              {agg.verified_count > 0 && ` · ${agg.verified_count} verified`}
            </p>
          </div>
        )}
      </div>

      {/* Existing user's review summary */}
      {myReview && !editing && (
        <div className="mt-4 bg-[#FAF8F5] border border-[#E5E1D8] p-4 rounded" data-testid="my-review-summary">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wider text-[#C9A961]">Your review</p>
            <button onClick={() => setEditing(true)} className="text-xs text-[#476B6B] hover:underline inline-flex items-center gap-1" data-testid="review-edit-mine">
              <Pencil size={11} strokeWidth={1.5} /> Edit
            </button>
          </div>
          <div className="mt-2"><StarRow value={myReview.rating} readOnly /></div>
          <p className="text-sm mt-2">{myReview.review_text}</p>
        </div>
      )}

      {/* Write or edit form */}
      {canShowForm && (
        <form onSubmit={submit} className="mt-4 space-y-3" data-testid="review-form">
          <p className="label">{myReview ? "Edit your review" : "Share your experience"}</p>
          <div className="flex items-center gap-3">
            <StarRow value={rating} onChange={setRating} size={22} />
            <span className="text-sm text-[#5C6B6B]">{rating} star{rating === 1 ? "" : "s"}</span>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What stood out? What helped? What would you tell someone considering this?"
            className="input-field min-h-[100px]"
            maxLength={4000}
            required
            data-testid="review-text"
          />
          <label className="flex items-center gap-2 text-xs text-[#5C6B6B]">
            <input type="checkbox" checked={anonymous} onChange={(e) => setAnonymous(e.target.checked)} data-testid="review-anon" />
            Post anonymously
          </label>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" data-testid="review-submit">
              {myReview ? "Save changes" : "Post review"}
            </button>
            {editing && (
              <button type="button" onClick={() => setEditing(false)} className="btn-outline">Cancel</button>
            )}
          </div>
        </form>
      )}

      {!isAuthenticated && (
        <p className="text-xs text-[#5C6B6B] mt-3">Sign in to leave a review.</p>
      )}

      {/* All reviews list */}
      <div className="mt-6">
        {loading ? (
          <p className="text-sm text-[#5C6B6B]">Loading reviews...</p>
        ) : reviews.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] py-6 text-center">No reviews yet. Be the first.</p>
        ) : (
          reviews.map((r) => (
            <ReviewItem
              key={r.id}
              review={r}
              currentUserId={user?.id}
              isAdmin={isAdmin}
              onReport={report}
              onModerate={moderate}
            />
          ))
        )}
      </div>
    </div>
  );
}
