/* EngravingGallery — minimal, 5-piece review page.
 *
 * URL: /engraving
 *
 * Shows nothing but the five final leather-patch designs, stacked vertically,
 * each on its own white canvas. Click any image to open / download at full
 * resolution.
 */
import React from "react";
import { Download } from "lucide-react";

const ITEMS = [
  { idx: "01", slug: "secure-connection",            phrase: "Secure connection is your birthright" },
  { idx: "02", slug: "founder-of-your-love-story",   phrase: "You are the founder of your own love story" },
  { idx: "03", slug: "created-for-connection",       phrase: "We are created for connection" },
  { idx: "04", slug: "the-bond-is-the-cure",         phrase: "The bond is the cure" },
  { idx: "05", slug: "repair-is-older-than-rupture", phrase: "Repair is older than rupture" },
];

const src = (it) =>
  `/engraving/birthright-engraving-${it.idx}-${it.slug}-rectangle-url-middle.png`;

export default function EngravingGallery() {
  return (
    <div className="bg-[#FAF8F5] min-h-screen" data-testid="engraving-gallery-page">
      <div className="container-page py-12 max-w-3xl">
        <div className="space-y-10">
          {ITEMS.map((it) => (
            <a
              key={it.idx}
              href={src(it)}
              target="_blank"
              rel="noopener noreferrer"
              download={`birthright-engraving-${it.idx}-${it.slug}.png`}
              className="block group"
              data-testid={`engraving-${it.idx}`}
              title={`Download — ${it.phrase}`}
            >
              <div className="relative bg-white border border-[#E5E1D8] rounded shadow-sm overflow-hidden group-hover:shadow-md transition">
                <img
                  src={src(it)}
                  alt={it.phrase}
                  className="w-full h-auto block"
                  loading="lazy"
                />
                <span className="absolute top-3 right-3 bg-white/90 backdrop-blur border border-[#E5E1D8] rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition" aria-label="Download">
                  <Download size={14} strokeWidth={1.6} className="text-[#1A2424]" />
                </span>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
