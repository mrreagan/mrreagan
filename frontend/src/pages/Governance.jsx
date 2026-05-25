import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Vote, FileText, ArrowRight } from "lucide-react";
import ShareButton from "../components/ShareButton";

export default function Governance() {
  const [members, setMembers] = useState([]);
  const [openRoles, setOpenRoles] = useState([]);

  useEffect(() => {
    api.get("/foundation/governing-members").then((r) => setMembers(r.data)).catch(() => {});
    api.get("/foundation-roles?open_only=true").then((r) => setOpenRoles(r.data)).catch(() => {});
  }, []);

  // map seeded_member_id -> role for cards that are currently being recruited for
  const memberRoleMap = openRoles.reduce((acc, role) => {
    if (role.seeded_member_id) acc[role.seeded_member_id] = role;
    return acc;
  }, {});

  return (
    <div className="container-page py-20" data-testid="governance-page">
      <div className="max-w-2xl">
        <span className="label">Governance</span>
        <h1 className="editorial-h1 mt-3">The people behind the work.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          A small group of practitioners, researchers, and stewards who keep the foundation accountable to its mission and to the people we serve.
        </p>
      </div>

      {openRoles.length > 0 && (
        <div className="mt-10 card p-6 bg-[#FFFBEF] border-l-4 border-[#C9A961]" data-testid="open-seats-banner">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="label text-[#8B7128]">{openRoles.length} open {openRoles.length === 1 ? "seat" : "seats"}</p>
              <p className="font-serif text-xl mt-1">We're seeking founding leadership for the foundation.</p>
              <p className="text-sm text-[#5C6B6B] mt-2">
                The cards below marked <em>"Sample — role we're seeking to fill"</em> are currently open positions.
              </p>
            </div>
            <Link to="/join-us" className="btn-primary inline-flex items-center gap-2" data-testid="banner-view-roles">
              View all open roles <ArrowRight size={14} strokeWidth={1.5} />
            </Link>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6 mt-10" data-testid="governing-members">
        {members.map((m) => {
          const role = memberRoleMap[m.id];
          const isOpen = Boolean(role);
          return (
            <div
              key={m.id}
              className={`card overflow-hidden flex flex-col sm:flex-row relative ${isOpen ? "ring-2 ring-[#C9A961]/40" : ""}`}
              data-testid={`member-${m.id}`}
            >
              {isOpen && (
                <span
                  className="absolute top-3 left-3 z-10 inline-flex items-center px-3 py-1 rounded-full text-[9px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424] shadow-sm"
                  data-testid={`sample-ribbon-${m.id}`}
                >
                  Sample — role we're seeking to fill
                </span>
              )}
              {m.image_url && (
                <div className="sm:w-48 shrink-0 bg-[#E5E1D8]">
                  <img src={m.image_url} alt={m.name} className={`w-full h-full object-cover aspect-square ${isOpen ? "opacity-70" : ""}`} />
                </div>
              )}
              <div className="p-6 flex-1">
                <span className="label">{m.title}</span>
                <h3 className="font-serif text-2xl mt-2">{m.name}</h3>
                {isOpen ? (
                  <>
                    <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed italic">
                      We're looking for someone like this: {m.bio}
                    </p>
                    <Link
                      to={`/join-us/${role.slug}`}
                      className="inline-flex items-center gap-1 text-sm text-[#476B6B] hover:underline mt-4"
                      data-testid={`apply-for-${role.slug}`}
                    >
                      Apply for this role <ArrowRight size={12} strokeWidth={1.5} />
                    </Link>
                  </>
                ) : (
                  <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{m.bio}</p>
                )}
                <div className="mt-4 flex items-center justify-end">
                  <ShareButton
                    surface="partner"
                    surfaceId={`board-${m.id}`}
                    path={`/governance#${m.id}`}
                    title={`${m.name} — ${m.title}`}
                    emailSubject={`Birthright governance: ${m.name}`}
                    size="sm"
                    allowBookmark={false}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="governance-callouts">
        <Link to="/governance/proposals" className="card p-6 hover:border-[#476B6B] transition" data-testid="link-proposals">
          <Vote size={20} strokeWidth={1.5} className="text-[#C9A961]" />
          <h3 className="font-serif text-xl mt-3">Proposals & voting</h3>
          <p className="text-sm text-[#5C6B6B] mt-1">Read every proposal in the open. Governance members vote. Anyone can debate.</p>
        </Link>
        <Link to="/legal/indemnification" className="card p-6 hover:border-[#476B6B] transition" data-testid="link-indemnification">
          <FileText size={20} strokeWidth={1.5} className="text-[#C9A961]" />
          <h3 className="font-serif text-xl mt-3">Universal indemnification</h3>
          <p className="text-sm text-[#5C6B6B] mt-1">One agreement, openly versioned, that participants and partners sign.</p>
        </Link>
      </div>
    </div>
  );
}
