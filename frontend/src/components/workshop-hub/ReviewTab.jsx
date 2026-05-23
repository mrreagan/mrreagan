import React from "react";
import ReviewSection from "../ReviewSection";

export default function ReviewTab({ workshop }) {
  return (
    <div className="max-w-3xl" data-testid="tab-review">
      <ReviewSection
        subjectType="workshop"
        subjectId={workshop.id}
        subjectLabel={`Reviews of ${workshop.title}`}
      />
    </div>
  );
}
