import React, { useState } from "react";
import { Star, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";

function RatingStars({ rating, onChange }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className="p-1"
          data-testid={`review-star-${s}`}
        >
          <Star size={28} strokeWidth={1.5} className={s <= rating ? "fill-[#C9A961] text-[#C9A961]" : "text-[#E5E1D8]"} />
        </button>
      ))}
    </div>
  );
}

function SubmittedConfirmation() {
  return (
    <div className="card p-8 mt-6 text-center">
      <CheckCircle2 size={36} strokeWidth={1.5} className="text-[#2E5C46] mx-auto" />
      <p className="text-sm text-[#1A2424] mt-3">Your review has been recorded. Thank you.</p>
    </div>
  );
}

export default function ReviewTab({ workshop }) {
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [anon, setAnon] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/reviews", {
        workshop_id: workshop.id,
        rating,
        review_text: text,
        anonymous: anon,
      });
      setSubmitted(true);
      toast.success("Thank you for your review");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit review");
    }
  };

  return (
    <div className="max-w-2xl" data-testid="tab-review">
      <span className="label">Your review</span>
      <h3 className="font-serif text-2xl mt-2">How was this workshop?</h3>
      {submitted ? (
        <SubmittedConfirmation />
      ) : (
        <form onSubmit={submit} className="card p-7 mt-6 space-y-5">
          <div>
            <label className="label block mb-3">Rating</label>
            <RatingStars rating={rating} onChange={setRating} />
          </div>
          <div>
            <label className="label block mb-2">Your review</label>
            <textarea
              required
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="input-field resize-none"
              data-testid="review-text"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[#5C6B6B]">
            <input
              type="checkbox"
              checked={anon}
              onChange={(e) => setAnon(e.target.checked)}
              className="accent-[#476B6B]"
              data-testid="review-anon"
            />
            Submit anonymously
          </label>
          <button type="submit" className="btn-primary w-full justify-center" data-testid="review-submit">
            Submit review
          </button>
        </form>
      )}
    </div>
  );
}
