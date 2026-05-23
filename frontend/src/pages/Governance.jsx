import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Vote, FileText } from "lucide-react";

export default function Governance() {
  const [members, setMembers] = useState([]);
  useEffect(() => {
    api.get("/foundation/governing-members").then((r) => setMembers(r.data)).catch(() => {});
  }, []);
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6 mt-14" data-testid="governing-members">
        {members.map((m) => (
          <div key={m.id} className="card overflow-hidden flex flex-col sm:flex-row" data-testid={`member-${m.id}`}>
            {m.image_url && (
              <div className="sm:w-48 shrink-0 bg-[#E5E1D8]">
                <img src={m.image_url} alt={m.name} className="w-full h-full object-cover aspect-square" />
              </div>
            )}
            <div className="p-6">
              <span className="label">{m.title}</span>
              <h3 className="font-serif text-2xl mt-2">{m.name}</h3>
              <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{m.bio}</p>
            </div>
          </div>
        ))}
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
