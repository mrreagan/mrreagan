import React, { useEffect, useMemo, useState, useCallback } from "react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import StarRow from "./reviews/StarRow";
import ReviewItem from "./reviews/ReviewItem";
import ReviewForm from "./reviews/ReviewForm";
import AggregateRatingBadgeImpl from "./reviews/AggregateRatingBadge";

// Re-export from the consolidated location so existing imports keep working.
export const AggregateRatingBadge = AggregateRatingBadgeImpl;

/**
 * <ReviewSection /> — orchestrator: loads reviews + aggregate, shows the
 * write-or-edit form for the current user, lists everyone else, wires up
 * report and moderate actions.
 *
 * Use anywhere a subject can be reviewed: workshop hubs, product details,
 * future vendor services.
 */
export default function ReviewSection({ subjectType, subjectId, subjectLabel }) {
  const { user } = useAuth();
  const isAuthenticated = !!user;
  const [reviews, setReviews] = useState([]);
  const [agg, setAgg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  const myReview = useMemo(
    () => (user ? reviews.find((r) => r.user_id === user.id) : null),
    [reviews, user]
  );

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.get(`/reviews?subject_type=${subjectType}&subject_id=${subjectId}`),
      api.get(`/reviews/aggregate?subject_type=${subjectType}&subject_id=${subjectId}`),
    ])
      .then(([rRes, aRes]) => { setReviews(rRes.data); setAgg(aRes.data); })
      .finally(() => setLoading(false));
  }, [subjectType, subjectId]);
  useEffect(() => { load(); }, [load]);

  const submit = async ({ rating, text, anonymous }) => {
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
      setEditing(false);
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

      {canShowForm && (
        <ReviewForm
          isEditing={!!myReview}
          initial={editing ? myReview : null}
          onSubmit={submit}
          onCancel={() => setEditing(false)}
        />
      )}

      {!isAuthenticated && (
        <p className="text-xs text-[#5C6B6B] mt-3">Sign in to leave a review.</p>
      )}

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
