import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { TierCard, DonationWidget } from "../components/sponsorship/SponsorshipParts";
import {
  NonDeductibleNotice,
  TaxStatusPill,
  FeaturedCampaignCard,
} from "../components/campaigns/CampaignParts";
import { ArrowRight } from "lucide-react";

export default function Sponsorship() {
  const [tiers, setTiers] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loadingTier, setLoadingTier] = useState(null);

  useEffect(() => {
    api.get("/checkout/sponsorship-tiers").then((r) => setTiers(r.data));
    api.get("/campaigns")
      .then((r) => setCampaigns(r.data?.campaigns || []))
      .catch(() => setCampaigns([]));
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
          Your sponsorship underwrites scholarships, facilitator training, and the slow work of building a foundation that doesn&apos;t gate-keep its tools. Choose a tier below — or fund a specific project through one of our active sponsor campaigns.
        </p>
        <NonDeductibleNotice className="mt-6" />
      </div>

      {campaigns.length > 0 && (
        <section className="mt-12" data-testid="sponsor-page-campaigns">
          <div className="flex items-baseline justify-between mb-5">
            <div>
              <span className="label text-[#8B4513]">Active sponsor campaigns</span>
              <h2 className="font-serif text-2xl lg:text-3xl text-[#0F2424] mt-1">
                Fund a specific project
              </h2>
            </div>
            <Link
              to="/campaigns"
              className="text-xs text-[#476B6B] hover:text-[#0F2424] inline-flex items-center gap-1"
              data-testid="all-campaigns-link"
            >
              View all <ArrowRight size={12} strokeWidth={1.5} />
            </Link>
          </div>
          <div className="space-y-6">
            {campaigns.map((c) => (
              <FeaturedCampaignCard key={c.id} campaign={c} testId={`sponsor-page-campaign-${c.slug}`} />
            ))}
          </div>
        </section>
      )}

      <section className="mt-16" data-testid="sponsorship-tier-section">
        <div className="mb-5">
          <span className="label">General sponsorship tiers</span>
          <h2 className="font-serif text-2xl lg:text-3xl text-[#0F2424] mt-1">
            Support the whole mission
          </h2>
          <p className="text-sm text-[#5C6B6B] mt-2 max-w-xl">
            Choose a tier to underwrite scholarships and facilitator training. Or give a custom amount below.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5" data-testid="sponsorship-tiers">
          {tiers.map((t) => (
            <TierCard key={t.id} tier={t} loading={loadingTier === t.id} onSelect={sponsor} />
          ))}
        </div>
      </section>

      <DonationWidget />
    </div>
  );
}
