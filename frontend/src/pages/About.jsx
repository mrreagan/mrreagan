import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { Heart, ArrowRight } from "lucide-react";

export default function About() {
  const [content, setContent] = useState(null);
  useEffect(() => {
    api.get("/foundation/content").then((r) => setContent(r.data)).catch(() => {});
  }, []);
  return (
    <div className="container-page py-20" data-testid="about-page">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-4">
          <span className="label">About the foundation</span>
          <h1 className="editorial-h1 mt-3">
            Born for<br />connection.
          </h1>
          <div className="divider-flame" />
          <p className="text-sm text-[#5C6B6B] leading-relaxed">
            An educational foundation devoted to one quiet conviction.
          </p>
        </div>
        <div className="lg:col-span-7 lg:col-start-6">
          <p className="text-lg text-[#1A2424] leading-relaxed">
            {content?.about_text || "Loading..."}
          </p>
          <div className="mt-12 flex flex-col gap-6">
            <div className="card p-7">
              <span className="label">Vision</span>
              <p className="font-serif text-xl mt-3 leading-snug">{content?.vision}</p>
            </div>
            <div className="card p-7 bg-[#F4F1EA]" data-testid="legacy-tile">
              <span className="label text-[#C9A961]">Legacy</span>
              <blockquote className="mt-3">
                <p className="font-serif text-lg text-[#1A2424] leading-relaxed">
                  &ldquo;Until now this has been a process supervised by professionals trained in EFT.
                  But it is so valuable and so needed that I have simplified the process so that you,
                  {" "}<em>dear reader</em>, can easily use it to change and grow your relationship.&rdquo;
                </p>
                <footer className="text-xs text-[#5C6B6B] mt-2">— Sue Johnson, 2008</footer>
              </blockquote>
              <blockquote className="mt-4 pt-4 border-t border-[#E5E1D8]">
                <p className="font-serif text-lg text-[#1A2424] leading-relaxed">
                  &ldquo;Indeed.&rdquo;
                </p>
                <footer className="text-xs text-[#5C6B6B] mt-2">— James Reagan, 2026</footer>
              </blockquote>
            </div>
            <div className="card p-7 !bg-[#476B6B] !border-[#476B6B] text-white">
              <Heart size={24} strokeWidth={1.5} className="text-[#C9A961]" />
              <p className="font-serif text-2xl mt-3 leading-snug" style={{ color: "white" }}>Support our work</p>
              <p className="text-sm text-white/80 mt-2">
                Sponsor a participant who couldn't otherwise attend, or join our community of regular givers.
              </p>
              <Link to="/sponsor" className="inline-flex items-center gap-1 text-sm font-medium text-[#C9A961] mt-4 hover:gap-2 transition-all" data-testid="about-sponsor-link">
                Become a sponsor <ArrowRight size={14} strokeWidth={1.5} />
              </Link>
            </div>
          </div>

          <div className="mt-14">
            <span className="label">Our values</span>
            <ul className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(content?.values || []).map((v) => (
                <li key={v} className="flex items-start gap-3 text-[#1A2424]" data-testid={`value-${v.replace(/\s+/g, "-").toLowerCase()}`}>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C9A961] mt-2.5 shrink-0" />
                  <span className="font-serif text-lg">{v}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
