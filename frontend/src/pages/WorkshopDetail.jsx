import React, { useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import useWorkshop from "../hooks/useWorkshop";
import {
  WorkshopHero,
  MaterialsList,
  WorkshopFaq,
  ReviewsList,
  PublicImpactPreview,
  LocationCard,
} from "../components/workshop/WorkshopSections";
import WorkshopRegistrationPanel from "../components/workshop/WorkshopRegistrationPanel";
import ShareButton from "../components/ShareButton";

export default function WorkshopDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const { workshop, reviews, publicImpacts, registered } = useWorkshop(slug, user);
  const [expandedFaq, setExpandedFaq] = useState(null);

  const avgRating = useMemo(() => {
    if (!reviews || reviews.length === 0) return null;
    return (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1);
  }, [reviews]);

  if (!workshop) {
    return (
      <div className="container-page py-20" data-testid="workshop-loading">
        Loading workshop...
      </div>
    );
  }

  const handleToggleFaq = (i) => setExpandedFaq((current) => (current === i ? null : i));

  return (
    <div data-testid="workshop-detail-page">
      <section className="bg-white border-b border-[#E5E1D8]">
        <div className="container-page py-12 grid grid-cols-1 lg:grid-cols-12 gap-10">
          <WorkshopHero workshop={workshop} avgRating={avgRating} reviewCount={reviews.length} />
          <WorkshopRegistrationPanel workshop={workshop} registered={registered} slug={slug} user={user} />
        </div>
      </section>

      <section className="container-page py-16 grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-8 space-y-12">
          <div className="flex items-center justify-between">
            <span className="label">About this workshop</span>
            <ShareButton
              surface="workshop"
              surfaceId={workshop.id}
              path={`/workshops/${workshop.slug}`}
              title={workshop.title}
              emailSubject={`Workshop: ${workshop.title}`}
              showLabel
            />
          </div>
          <div>
            <p className="text-base text-[#1A2424] leading-relaxed whitespace-pre-line">
              {workshop.full_description}
            </p>
          </div>
          <MaterialsList items={workshop.materials_included} />
          <WorkshopFaq faq={workshop.faq} expandedIdx={expandedFaq} onToggle={handleToggleFaq} />
          <ReviewsList reviews={reviews} />
          <PublicImpactPreview impacts={publicImpacts} />
        </div>
        <LocationCard workshop={workshop} />
      </section>
    </div>
  );
}
