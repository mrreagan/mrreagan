import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import ShareButton from "../components/ShareButton";

export default function Facilitators() {
  const [facs, setFacs] = useState([]);
  useEffect(() => {
    api.get("/facilitators").then((r) => setFacs(r.data));
  }, []);
  return (
    <div className="container-page py-16" data-testid="facilitators-page">
      <div className="max-w-2xl">
        <span className="label">Facilitators</span>
        <h1 className="editorial-h1 mt-3">The people who hold the room.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Trained, credentialed, and chosen for the quality of their presence as much as their expertise. Each facilitator brings their own lineage to the work.
        </p>
      </div>
      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {facs.map((f) => <FacilitatorCard key={f.id} f={f} />)}
      </div>
    </div>
  );
}

function FacilitatorCard({ f }) {
  const navigate = useNavigate();
  const slug = f.facilitator_slug || f.id;
  const go = () => navigate(`/facilitators/${slug}`);
  return (
    <div
      role="link"
      tabIndex={0}
      onClick={go}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") go(); }}
      className="card card-hover overflow-hidden block cursor-pointer"
      data-testid={`facilitator-${f.id}`}
    >
      {f.avatar_url && (
        <div className="aspect-[4/5] bg-[#E5E1D8] overflow-hidden">
          <img src={f.avatar_url} alt={f.first_name} className="w-full h-full object-cover" />
        </div>
      )}
      <div className="p-6">
        <span className="label">{f.credentials || "Facilitator"}</span>
        <h3 className="font-serif text-2xl mt-2">{f.first_name} {f.last_name}</h3>
        <div className="mt-3 flex items-center justify-between gap-2">
          <p className="text-xs text-[#5C6B6B]">{f.workshop_count} workshop{f.workshop_count !== 1 ? "s" : ""} on the calendar</p>
          <ShareButton
            surface="facilitator"
            surfaceId={slug}
            path={`/facilitators/${slug}`}
            title={`${f.first_name} ${f.last_name}`}
            emailSubject={`Birthright facilitator: ${f.first_name} ${f.last_name}`}
            size="sm"
            stopPropagation
          />
        </div>
      </div>
    </div>
  );
}
