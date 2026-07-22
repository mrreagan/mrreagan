import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { TierCard, DonationWidget } from "../components/sponsorship/SponsorshipParts";
import { NonDeductibleNotice, TaxStatusPill } from "../components/campaigns/CampaignParts";
import { ArrowRight } from "lucide-react";

export default function Sponsorship() {
  const [tiers, setTiers] = useState([]);
  const [loadingTier, setLoadingTier] = useState(null);

  useEffect(() => {
    api.get("/checkout/sponsorship-tiers").then((r) => setTiers(r.data));
  }, []);

  const sponsor = async (tierId) => {
    setLoadingTier(tierId);
    try {
      const { data } = await api.post("/checkout/sponsorship", {
        tier_id: tierId,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setLoadingTier(null);
    }
  };

  return (
    <div className="container-page py-16" data-testid="sponsorship-page">
      <div className="max-w-2xl">
        <span className="label">Sponsorship</span>
        <TaxStatusPill className="ml-2" />
        <h1 className="editorial-h1 mt-3">Help someone claim their birthright.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Your sponsorship underwrites scholarships, facilitator training, and the slow work of building a foundation that doesn't gate-keep its tools. Choose a tier, or give what feels right.
        </p>
        <NonDeductibleNotice className="mt-6" />
        <p className="text-xs text-[#5C6B6B] mt-4">
          Looking to fund a specific project?{" "}
          <Link to="/campaigns" className="underline hover:text-[#C9A961]">
            See active sponsor campaigns <ArrowRight size={12} strokeWidth={1.5} className="inline" />
          </Link>
        </p>
      </div>

      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5" data-testid="sponsorship-tiers">
        {tiers.map((t) => (
          <TierCard key={t.id} tier={t} loading={loadingTier === t.id} onSelect={sponsor} />
        ))}
      </div>

      <DonationWidget />
    </div>
  );
}
