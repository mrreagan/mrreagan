/* MarketingIndex — internal index for non-public marketing materials.
 *
 * URL: /marketing
 *
 * Not linked from public navigation. Reachable only by direct URL.
 * Lists campaign packs as tiles; add new packs by appending to CAMPAIGNS.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

const CAMPAIGNS = [
  {
    href: "/fb-promo",
    eyebrow: "Facebook · launched Feb 2026",
    title: "Patch Pack — five attachment-theory phrases",
    blurb: (
      <>
        Five engraved leather patches photographed flat-lay with brand-aligned
        signature objects (signet ring · fountain pen · paired cups · key ·
        kintsugi dish). Each phrase delivered as a landscape{" "}
        <em>1920×1080</em> social card with the verbatim "What this means"
        copy in brand teal and gold, plus matching portrait card and bare
        hero. Recommended format: landscape v4.
      </>
    ),
    cover: "/fb-assets/v4-landscape/fb-ls-01-secure-connection.png",
    count: "5 × landscape · 5 × portrait · 5 × hero",
  },
  // Future campaigns slot in here ↓
  // {
  //   href: "/instagram-pack-2026",
  //   eyebrow: "Instagram · 2026 Q2",
  //   title: "…",
  //   …
  // },
];

export default function MarketingIndex() {
  return (
    <div
      className="min-h-screen bg-[#F8F2E5]"
      data-testid="marketing-index-page"
    >
      <div className="max-w-5xl mx-auto px-5 py-12 sm:py-16">
        <header className="mb-12 sm:mb-16">
          <p className="text-xs uppercase tracking-[0.25em] text-[#A87A4A] mb-3">
            Internal · link-only
          </p>
          <h1 className="text-3xl sm:text-5xl font-serif italic text-[#2C4E5A] leading-tight">
            Marketing materials
          </h1>
          <p className="text-sm text-[#3D6373] mt-4 max-w-2xl leading-relaxed">
            A non-public workspace for campaign assets — Facebook, Instagram,
            print, partner kits. This page is not in the site navigation and
            is not indexed; only people with the direct URL can reach it.
          </p>
        </header>

        <div className="space-y-10">
          {CAMPAIGNS.map((c) => (
            <Link
              key={c.href}
              to={c.href}
              data-testid={`marketing-campaign-${c.href.replace(/[^a-z0-9]/gi, "")}`}
              className="group grid sm:grid-cols-[1fr_1.2fr] gap-6 border-t border-[#E5DCC4] pt-8 hover:bg-white/30 transition-colors"
            >
              <div className="bg-white/40 border border-[#E5DCC4] overflow-hidden">
                <img
                  src={c.cover}
                  alt={c.title}
                  className="w-full h-auto block"
                  loading="lazy"
                />
              </div>
              <div className="flex flex-col">
                <p className="text-[11px] uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
                  {c.eyebrow}
                </p>
                <h2 className="text-2xl sm:text-3xl font-serif italic text-[#2C4E5A] leading-snug">
                  {c.title}
                </h2>
                <p className="text-[#3D6373] text-base sm:text-[17px] leading-relaxed mt-4 font-serif italic">
                  {c.blurb}
                </p>
                <p className="text-xs uppercase tracking-[0.2em] text-[#A87A4A] mt-5">
                  {c.count}
                </p>
                <div className="mt-auto pt-6 flex items-center gap-2 text-[#2C4E5A] text-sm">
                  <span className="font-serif italic group-hover:underline">
                    Open the pack
                  </span>
                  <ArrowUpRight size={16} strokeWidth={1.6} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>

        <footer className="mt-20 pt-10 border-t border-[#E5DCC4] text-xs text-[#A87A4A] tracking-[0.2em] uppercase">
          birthright.live · internal preview
        </footer>
      </div>
    </div>
  );
}
