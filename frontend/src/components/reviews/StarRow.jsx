import React from "react";
import { Star } from "lucide-react";

/**
 * Five-star input/display row.
 * Pass `readOnly` for display; otherwise `onChange(newValue)` fires on click.
 */
export default function StarRow({ value, onChange, readOnly = false, size = 16 }) {
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
