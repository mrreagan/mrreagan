import React, { useEffect, useState } from "react";
import StarRow from "./StarRow";

/**
 * Write-or-edit review form. Internal state seeded from `initial` so that
 * editing pre-fills correctly.
 *
 * Props:
 *   isEditing — true when the user is editing their existing review
 *   initial   — {rating, review_text, anonymous} to prefill (null when writing new)
 *   onSubmit  — async ({rating, text, anonymous}) => void
 *   onCancel  — when editing, called to close the form without saving
 */
export default function ReviewForm({ isEditing, initial, onSubmit, onCancel }) {
  const [rating, setRating] = useState(initial?.rating ?? 5);
  const [text, setText] = useState(initial?.review_text ?? "");
  const [anonymous, setAnonymous] = useState(initial?.anonymous ?? false);

  useEffect(() => {
    if (initial) {
      setRating(initial.rating ?? 5);
      setText(initial.review_text ?? "");
      setAnonymous(initial.anonymous ?? false);
    }
  }, [initial]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ rating, text, anonymous });
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 space-y-3" data-testid="review-form">
      <p className="label">{isEditing ? "Edit your review" : "Share your experience"}</p>
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
          {isEditing ? "Save changes" : "Post review"}
        </button>
        {isEditing && (
          <button type="button" onClick={onCancel} className="btn-outline">Cancel</button>
        )}
      </div>
    </form>
  );
}
