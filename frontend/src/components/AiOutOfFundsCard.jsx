/**
 * Shared "out of funds" / "low balance" card used by:
 *   - ResearchAIPanel
 *   - VendorPDMPanel
 *   - AssistantWidget Concierge (only renders when balance gate blocks)
 *
 * Always provides TWO escapes:
 *   1. "Top up" button → navigates to /dashboard/ai-wallet (closes panel)
 *   2. "Close" / "Back" button → calls onClose()
 *
 * The user should NEVER be stuck looking at an error with no way out.
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import { Wallet, ArrowLeft } from "lucide-react";

export default function AiOutOfFundsCard({ balance, minNeeded, onClose }) {
  const navigate = useNavigate();
  const goToWallet = () => {
    if (onClose) onClose();
    navigate("/dashboard/ai-wallet");
  };
  return (
    <div className="rounded-xl border border-[#C9A961] bg-[#FFF8E1] p-4 my-3" data-testid="out-of-funds-card">
      <div className="flex items-start gap-2 mb-2">
        <Wallet size={16} strokeWidth={1.6} className="text-[#8B7128] mt-0.5 flex-shrink-0" />
        <div>
          <p className="font-medium text-[#8B7128]">AI wallet is low</p>
          <p className="text-sm text-[#5C6B6B] mt-1">
            Your balance is <b>${(balance ?? 0).toFixed(4)}</b>
            {minNeeded != null && <> — this action needs about <b>${minNeeded.toFixed(4)}</b></>}.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 mt-3">
        <button onClick={goToWallet} className="btn-primary text-xs inline-flex items-center gap-1" data-testid="out-of-funds-topup-btn">
          <Wallet size={11} strokeWidth={1.8} /> Top up now
        </button>
        <button onClick={onClose} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="out-of-funds-back-btn">
          <ArrowLeft size={11} strokeWidth={1.8} /> Back to page
        </button>
      </div>
    </div>
  );
}

/** Header pill that shows live balance + tap-to-topup. */
export function AiBalancePill({ balance, onTopup }) {
  const low = (balance ?? 0) < 1.0;
  return (
    <button
      onClick={onTopup}
      className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-medium px-2.5 py-1 rounded-full border ${
        low ? "bg-[#FFF8E1] text-[#8B7128] border-[#C9A961]" : "bg-white text-[#5C6B6B] border-[#E5E1D8]"
      }`}
      data-testid="ai-balance-pill"
      title="Open AI Wallet"
    >
      <Wallet size={10} strokeWidth={1.8} />
      ${(balance ?? 0).toFixed(2)}
      {low && <span className="ml-1">low</span>}
    </button>
  );
}
