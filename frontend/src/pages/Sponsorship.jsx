import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { Gem, ArrowRight, Heart } from "lucide-react";
import { toast } from "sonner";

const TIER_COLORS = {
  amethyst: "from-[#7C5295] to-[#A570CB]",
  ruby: "from-[#9E1B32] to-[#C7384F]",
  sapphire: "from-[#1E3A8A] to-[#3B5DAB]",
  emerald: "from-[#1F6E55] to-[#3E9B7B]",
  diamond: "from-[#5C6B6B] to-[#9CA9A9]",
};

export default function Sponsorship() {
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(null);
  const [donateAmount, setDonateAmount] = useState("50");

  useEffect(() => {
    api.get("/checkout/sponsorship-tiers").then((r) => setTiers(r.data));
  }, []);

  const sponsor = async (tier_id) => {
    setLoading(tier_id);
    try {
      const { data } = await api.post("/checkout/sponsorship", {
        tier_id,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setLoading(null);
    }
  };

  const donate = async (e) => {
    e.preventDefault();
    const amount = parseFloat(donateAmount);
    if (!amount || amount < 1) return;
    setLoading("donate");
    try {
      const { data } = await api.post("/checkout/donation", { amount, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setLoading(null);
    }
  };

  return (
    <div className="container-page py-16" data-testid="sponsorship-page">
      <div className="max-w-2xl">
        <span className="label">Sponsorship</span>
        <h1 className="editorial-h1 mt-3">Help someone claim their birthright.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Your sponsorship underwrites scholarships, facilitator training, and the slow work of building a foundation that doesn't gate-keep its tools. Choose a tier, or give what feels right.
        </p>
      </div>

      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5" data-testid="sponsorship-tiers">
        {tiers.map((t) => (
          <div key={t.id} className="card p-6 flex flex-col" data-testid={`tier-${t.id}`}>
            <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${TIER_COLORS[t.id]} flex items-center justify-center`}>
              <Gem size={20} strokeWidth={1.5} className="text-white" />
            </div>
            <p className="font-serif text-2xl mt-4">{t.name.replace(" Sponsor", "")}</p>
            <p className="font-serif text-4xl text-[#1A2424] mt-1">${t.amount?.toFixed(0)}</p>
            <p className="text-xs text-[#5C6B6B] mt-4 flex-1 leading-relaxed">{t.perks}</p>
            <button
              onClick={() => sponsor(t.id)}
              disabled={loading === t.id}
              className="btn-primary mt-5 w-full justify-center text-sm"
              data-testid={`tier-cta-${t.id}`}
            >
              {loading === t.id ? "Loading..." : <>Sponsor <ArrowRight size={14} strokeWidth={1.5} /></>}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-16 card p-10 lg:p-14 bg-[#476B6B] border-[#476B6B]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div className="text-white">
            <Heart size={28} strokeWidth={1.5} className="text-[#C9A961]" />
            <h2 className="editorial-h2 mt-4" style={{ color: "white" }}>Or give what feels right.</h2>
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
                value={donateAmount}
                onChange={(e) => setDonateAmount(e.target.value)}
                className="bg-transparent outline-none flex-1 ml-2"
                data-testid="donate-amount"
              />
            </div>
            <button type="submit" disabled={loading === "donate"} className="btn-accent" data-testid="donate-submit">
              {loading === "donate" ? "..." : "Donate"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
