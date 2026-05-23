import React, { useState } from "react";
import StarRow from "./StarRow";
import { ShieldCheck, Flag, EyeOff } from "lucide-react";

/**
 * One review row inside a list: stars + author + verified badge + body,
 * plus inline report and admin moderate controls.
 */
export default function ReviewItem({ review, currentUserId, isAdmin, onReport, onModerate }) {
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
