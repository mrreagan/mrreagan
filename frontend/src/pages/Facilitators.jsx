import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";

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
        {facs.map((f) => (
          <Link
            key={f.id}
            to={`/facilitators/${f.facilitator_slug || f.id}`}
            className="card card-hover overflow-hidden block"
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
              <p className="text-xs text-[#5C6B6B] mt-3">{f.workshop_count} workshop{f.workshop_count !== 1 ? "s" : ""} on the calendar</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
