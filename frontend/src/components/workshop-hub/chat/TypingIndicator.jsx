import React from "react";

/**
 * Animated "X is typing…" indicator. Renders nothing when no one is typing.
 */
export default function TypingIndicator({ names }) {
  if (!names.length) return null;
  const label =
    names.length === 1 ? `${names[0]} is typing…`
    : names.length === 2 ? `${names[0]} and ${names[1]} are typing…`
    : `${names.length} people are typing…`;
  return (
    <div className="flex items-center gap-2 text-xs text-[#5C6B6B] italic px-1" data-testid="chat-typing">
      <span className="inline-flex gap-0.5">
        <span className="w-1 h-1 rounded-full bg-[#5C6B6B] animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-1 h-1 rounded-full bg-[#5C6B6B] animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-1 h-1 rounded-full bg-[#5C6B6B] animate-bounce" style={{ animationDelay: "300ms" }} />
      </span>
      {label}
    </div>
  );
}
