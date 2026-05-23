import React from "react";

/**
 * Left rail listing the conversations available in a workshop hub chat:
 * the group thread plus one row per fellow participant for DMs. Presence
 * dot lights up when that user is currently connected via WebSocket.
 */
export default function ParticipantsSidebar({ participants, recipientId, onSelect, presenceIds }) {
  return (
    <div className="card p-4 lg:max-h-[600px] lg:overflow-y-auto" data-testid="chat-participants">
      <span className="label">Conversations</span>
      <button
        onClick={() => onSelect(null)}
        className={`block w-full text-left mt-3 px-3 py-2 rounded-lg text-sm ${!recipientId ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"}`}
        data-testid="chat-group"
      >
        # Group chat
      </button>
      <div className="mt-2 space-y-1">
        {participants.map((p) => {
          const online = presenceIds.has(p.id);
          const active = recipientId === p.id;
          return (
            <button
              key={p.id}
              onClick={() => onSelect(p.id)}
              className={`flex items-center justify-between w-full text-left px-3 py-2 rounded-lg text-sm ${active ? "bg-[#476B6B] text-white" : "hover:bg-[#FAF8F5]"}`}
              data-testid={`chat-user-${p.id}`}
            >
              <span>
                {p.name}
                {p.role === "facilitator" && <span className="text-[10px] uppercase tracking-wider ml-1 opacity-70">facilitator</span>}
              </span>
              {online && <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-white" : "bg-[#2E5C46]"}`} title="online" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
