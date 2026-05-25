import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { ArrowRight, Heart, Clock } from "lucide-react";
import ShareButton from "../components/ShareButton";

export default function JoinUs() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/foundation-roles?open_only=true")
      .then((r) => setRoles(r.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="container-page py-16" data-testid="join-us-page">
      <div className="max-w-3xl">
        <span className="label">Join Us</span>
        <h1 className="editorial-h1 mt-3">Help us build the foundation.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Birthright is at the stage where the right people in the right seats can shape what the
          foundation becomes. The three roles below are currently open. All are equity-in-mission —
          Birthright is a not-for-profit and does not currently provide monetary compensation.
          Stipends, honoraria, and grant-funded engagement may emerge as funding allows.
        </p>
      </div>

      <div className="mt-12 space-y-6" data-testid="join-us-roles">
        {loading && <p className="text-sm text-[#5C6B6B]">Loading open roles...</p>}
        {!loading && roles.length === 0 && (
          <div className="card p-10 text-center">
            <p className="font-serif text-lg">No open roles right now.</p>
            <p className="text-xs text-[#5C6B6B] mt-2">Check back soon — we recruit in cohorts.</p>
          </div>
        )}
        {roles.map((role) => <RoleCard key={role.slug} role={role} />)}
      </div>

      <div className="mt-16 card p-8 bg-[#FFFBEF]" data-testid="join-us-footer-note">
        <p className="label text-[#8B7128]">A note on equity in mission</p>
        <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">
          These roles are unpaid in the traditional sense. We're recruiting people whose own
          professional standing makes them able to invest a portion of their time in building
          something that doesn't yet exist. As the foundation matures and funding is secured —
          through grants, founding-partner subscriptions, and donor relationships — we expect
          stipends and honoraria to emerge for board service. We can't promise that today. We
          can promise transparency about it as it evolves.
        </p>
      </div>
    </div>
  );
}

function RoleCard({ role }) {
  return (
    <div className="card overflow-hidden" data-testid={`role-card-${role.slug}`}>
      <div className="p-6 md:p-8">
        <div className="flex flex-wrap items-start gap-3 mb-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-medium bg-[#476B6B] text-white">
            Open Role
          </span>
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-medium bg-[#2E5C46] text-white">
            <Heart size={10} strokeWidth={2} /> Equity in Mission
          </span>
          {role.time_commitment && (
            <span className="inline-flex items-center gap-1 text-xs text-[#5C6B6B]">
              <Clock size={12} strokeWidth={1.5} />
              {role.time_commitment}
            </span>
          )}
        </div>
        <h2 className="font-serif text-3xl text-[#1A2424]" data-testid={`role-title-${role.slug}`}>{role.title}</h2>
        <p className="text-base text-[#476B6B] mt-2 leading-snug">{role.headline}</p>

        <div className="grid md:grid-cols-3 gap-6 mt-6">
          <div>
            <p className="label mb-2 text-[#8B7128]">Who you are</p>
            <p className="text-sm text-[#1A2424] leading-relaxed">{role.who_you_are}</p>
          </div>
          <div>
            <p className="label mb-2 text-[#8B7128]">What you'll do</p>
            <p className="text-sm text-[#1A2424] leading-relaxed">{role.what_youll_do}</p>
          </div>
          <div>
            <p className="label mb-2 text-[#8B7128]">What you bring</p>
            <p className="text-sm text-[#1A2424] leading-relaxed">{role.what_you_bring}</p>
          </div>
        </div>

        <div className="mt-6 pt-5 border-t border-[#E5E1D8] flex items-center justify-between gap-3 flex-wrap">
          <p className="text-xs text-[#5C6B6B] max-w-md">{role.compensation_summary}</p>
          <div className="flex items-center gap-2">
            <ShareButton
              surface="foundation_role"
              surfaceId={role.slug}
              path={`/join-us/${role.slug}`}
              title={role.title}
              emailSubject={`Open role at Birthright: ${role.title}`}
              size="sm"
            />
            <Link
              to={`/join-us/${role.slug}`}
              className="btn-primary inline-flex items-center gap-2 text-sm"
              data-testid={`apply-${role.slug}`}
            >
              Apply for this role
              <ArrowRight size={14} strokeWidth={1.5} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
