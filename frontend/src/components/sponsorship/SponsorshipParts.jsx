import React, { useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";
import { Gem, ArrowRight, Heart } from "lucide-react";

const TIER_COLORS = {
  amethyst: "from-[#7C5295] to-[#A570CB]",
  ruby: "from-[#9E1B32] to-[#C7384F]",
  sapphire: "from-[#1E3A8A] to-[#3B5DAB]",
  emerald: "from-[#1F6E55] to-[#3E9B7B]",
  diamond: "from-[#5C6B6B] to-[#9CA9A9]",
};

// ---------- Single tier card ----------
export function TierCard({ tier, loading, onSelect }) {
  return (
    <div className="card p-6 flex flex-col" data-testid={`tier-${tier.id}`}>
      <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${TIER_COLORS[tier.id]} flex items-center justify-center`}>
        <Gem size={20} strokeWidth={1.5} className="text-white" />
      </div>
      <p className="font-serif text-2xl mt-4">{tier.name.replace(" Sponsor", "")}</p>
      <p className="font-serif text-4xl text-[#1A2424] mt-1">${tier.amount?.toFixed(0)}</p>
      <p className="text-xs text-[#5C6B6B] mt-4 flex-1 leading-relaxed">{tier.perks}</p>
      <button
        onClick={() => onSelect(tier.id)}
        disabled={loading}
        className="btn-primary mt-5 w-full justify-center text-sm"
        data-testid={`tier-cta-${tier.id}`}
      >
        {loading ? "Loading..." : (<>Sponsor <ArrowRight size={14} strokeWidth={1.5} /></>)}
      </button>
    </div>
  );
}

// ---------- Donation widget ----------
export function DonationWidget() {
  const [amount, setAmount] = useState("50");
  const [loading, setLoading] = useState(false);

  const donate = async (e) => {
    e.preventDefault();
    const value = parseFloat(amount);
    if (!value || value < 1) return;
    setLoading(true);
    try {
      const { data } = await api.post("/checkout/donation", { amount: value, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setLoading(false);
    }
  };

  return (
    <div className="mt-16 card p-10 lg:p-14 bg-[#476B6B] border-[#476B6B]">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
        <div className="text-white">
          <Heart size={28} strokeWidth={1.5} className="text-[#C9A961]" />
          <h2 className="editorial-h2 mt-4" style={{ color: "white" }}>
            Or give what feels right.
          </h2>
          <p className="text-white/80 mt-3 text-sm leading-relaxed">
            One-time gift in any amount. Every dollar supports scholarships and the foundation's educational work.
          </p>
        </div>
        <form onSubmit={donate} className="flex gap-3" data-testid="donation-form">
          <div className="flex items-center input-field !py-2 flex-1">
            <span className="text-[#5C6B6B]">$</span>
            <input
              type="number"
              min="1"
              step="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="bg-transparent outline-none flex-1 ml-2"
              data-testid="donate-amount"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-accent" data-testid="donate-submit">
            {loading ? "..." : "Donate"}
          </button>
        </form>
      </div>
    </div>
  );
}
