/** Button that opens a DM thread with another user. */
import React from "react";
import { useNavigate } from "react-router-dom";
import { MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";

export default function MessageButton({
  recipientId,
  recipientName,
  size = "default",      // 'sm' | 'default'
  showLabel = true,
  className = "",
  testid,
  stopPropagation = false,
}) {
  const navigate = useNavigate();
  const { user } = useAuth();
  if (!recipientId) return null;
  // Hide the button when viewing your own profile
  if (user && user.id === recipientId) return null;

  const sizeCls = size === "sm"
    ? "px-2 py-1 text-[11px]"
    : "px-3 py-1.5 text-xs";

  const go = (e) => {
    if (stopPropagation) e.stopPropagation();
    if (!user) {
      toast.message("Sign in to message a partner", { description: "Direct messages are between birthright members and partners." });
      navigate("/auth/login");
      return;
    }
    navigate(`/dashboard/messages?to=${recipientId}`);
  };

  return (
    <button
      type="button"
      onClick={go}
      className={`inline-flex items-center gap-1.5 rounded-full border border-[#E5E1D8] bg-white hover:border-[#476B6B] hover:bg-[#FAF8F5] transition ${sizeCls} ${className}`}
      data-testid={testid || `message-button-${recipientId}`}
      title={recipientName ? `Message ${recipientName}` : "Message"}
    >
      <MessageCircle size={14} strokeWidth={1.5} />
      {showLabel && <span className="uppercase tracking-wider">Message</span>}
    </button>
  );
}
