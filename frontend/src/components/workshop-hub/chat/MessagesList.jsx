import React from "react";

function MessageBubble({ message, isMine }) {
  return (
    <div className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${isMine ? "bg-[#476B6B] text-white" : "bg-[#FAF8F5] text-[#1A2424]"}`}>
        {!isMine && <p className="text-[10px] uppercase tracking-wider opacity-60 mb-0.5">{message.sender_name}</p>}
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
      </div>
    </div>
  );
}

/**
 * Scroll-anchored chat message list. Caller passes the ref so it can scroll
 * to the bottom whenever new messages arrive.
 */
export default function MessagesList({ messages, currentUserId, scrollRef }) {
  return (
    <div ref={scrollRef} className="flex-1 mt-4 overflow-y-auto space-y-3 max-h-[420px] pr-2" data-testid="chat-messages">
      {messages.length === 0 && <p className="text-sm text-[#5C6B6B] text-center py-10">No messages yet.</p>}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} isMine={m.sender_id === currentUserId} />
      ))}
    </div>
  );
}
