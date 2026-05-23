import React from "react";
import { Wifi, WifiOff, Loader2 } from "lucide-react";

const STATUS_CONFIG = {
  connecting:   { label: "Connecting…",  cls: "bg-[#FAF8F5] text-[#5C6B6B]",     icon: Loader2, spin: true },
  connected:    { label: "Live",         cls: "bg-[#2E5C46]/10 text-[#2E5C46]",   icon: Wifi },
  reconnecting: { label: "Reconnecting…", cls: "bg-[#C9A961]/15 text-[#C9A961]",  icon: Loader2, spin: true },
  fallback:     { label: "Slow mode",    cls: "bg-[#C9A961]/15 text-[#C9A961]",   icon: WifiOff },
  offline:      { label: "Offline",      cls: "bg-[#B86A5C]/10 text-[#B86A5C]",   icon: WifiOff },
};

export default function ConnectionPill({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: status, cls: "bg-[#FAF8F5]", icon: Wifi };
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${cfg.cls}`} data-testid={`chat-status-${status}`}>
      <Icon size={10} strokeWidth={2} className={cfg.spin ? "animate-spin" : ""} />
      {cfg.label}
    </span>
  );
}
