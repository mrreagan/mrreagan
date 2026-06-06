/* EngravingGallery — internal review page that shows every generated
 * engraving image variation in one branded space.
 *
 * URL: /engraving (React route)
 *
 * Layout:
 *   - Section per phrase
 *   - Tabs: Rectangle / Hexagon
 *   - Within each tab, the 3 URL placements rendered side-by-side
 *   - Each tile has a click-to-download link + the placement label
 *
 * This page is intentionally NOT linked from any public nav — it's an
 * internal workshop / review page for the founder. Share the URL directly
 * with collaborators who need to pick favorites.
 */
import React, { useState } from "react";
import { Flame, Download, ImageOff } from "lucide-react";

const PHRASES = [
  { idx: "01", slug: "secure-connection",            phrase: "Secure connection is your birthright",         emphasis: "“birthright” in upright roman" },
  { idx: "02", slug: "founder-of-your-love-story",   phrase: "You are the founder of your own love story",   emphasis: "“your own” italic + slightly larger" },
  { idx: "03", slug: "created-for-connection",       phrase: "We are created for connection",                emphasis: "no emphasis · uniform italic" },
  { idx: "04", slug: "the-bond-is-the-cure",         phrase: "The bond is the cure",                         emphasis: "no emphasis · uniform italic" },
  { idx: "05", slug: "repair-is-older-than-rupture", phrase: "Repair is older than rupture",                 emphasis: "no emphasis · uniform italic" },
];

const SHAPES = [
  { id: "rectangle", label: "Rectangle" },
  { id: "hexagon",   label: "Hexagon" },
];

const PLACEMENTS = [
  { id: "top",    label: "URL · top" },
  { id: "middle", label: "URL · middle" },
  { id: "bottom", label: "URL · bottom" },
];

const fileFor = (p, shape, placement) =>
  `/engraving/birthright-engraving-${p.idx}-${p.slug}-${shape}-url-${placement}.png`;

export default function EngravingGallery() {
  const [shape, setShape] = useState("rectangle");

  return (
    <div className="bg-[#FAF8F5] min-h-screen" data-testid="engraving-gallery-page">
      <div className="container-page py-16">
        <div className="max-w-3xl">
          <span className="label inline-flex items-center gap-2">
            <Flame size={12} strokeWidth={1.6} className="text-[#C9A961]" /> Internal · Engraving studio
          </span>
          <h1 className="editorial-h1 mt-3">Leather patch designs.</h1>
          <div className="divider-flame" />
          <p className="text-sm text-[#5C6B6B] leading-relaxed">
            Five phrases &times; two patch shapes &times; three URL placements.
            Each image is a horizontal {shape} leather-patch design in solid black,
            ready to be sent to a laser engraver. Click any image to download the
            full-resolution PNG.
          </p>
        </div>

        {/* Shape switcher */}
        <div className="flex gap-2 mt-8" data-testid="shape-switcher">
          {SHAPES.map((s) => (
            <button
              key={s.id}
              onClick={() => setShape(s.id)}
              className={`px-5 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
                shape === s.id
                  ? "bg-[#476B6B] text-white border-[#476B6B]"
                  : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`shape-${s.id}`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* One section per phrase */}
        <div className="mt-10 space-y-14">
          {PHRASES.map((p) => (
            <PhraseSection key={p.idx} phrase={p} shape={shape} />
          ))}
        </div>

        <p className="text-xs text-[#5C6B6B] italic mt-16">
          Tip: right-click any tile and choose &ldquo;Save image as&hellip;&rdquo; or click the
          download icon to grab the file at full resolution.
        </p>
      </div>
    </div>
  );
}

function PhraseSection({ phrase, shape }) {
  return (
    <section data-testid={`phrase-section-${phrase.idx}`}>
      <div className="flex items-baseline gap-3 mb-1">
        <span className="font-serif text-xl text-[#C9A961]">{phrase.idx}</span>
        <h2 className="font-serif text-2xl italic text-[#1A2424]">
          {phrase.phrase}
        </h2>
      </div>
      <p className="text-[11px] uppercase tracking-wider text-[#5C6B6B] mb-5">
        Emphasis: <span className="text-[#476B6B] not-italic font-medium">{phrase.emphasis}</span>
      </p>

      <div className="grid md:grid-cols-3 gap-5">
        {PLACEMENTS.map((pl) => (
          <ImageTile
            key={pl.id}
            src={fileFor(phrase, shape, pl.id)}
            label={pl.label}
            downloadName={`birthright-engraving-${phrase.idx}-${phrase.slug}-${shape}-url-${pl.id}.png`}
          />
        ))}
      </div>
    </section>
  );
}

function ImageTile({ src, label, downloadName }) {
  const [errored, setErrored] = useState(false);
  return (
    <div className="card overflow-hidden" data-testid={`tile-${downloadName}`}>
      <div className="aspect-[3/2] bg-white border-b border-[#E5E1D8] flex items-center justify-center overflow-hidden">
        {errored ? (
          <div className="flex flex-col items-center text-[#9E3C3C] text-xs gap-2 p-4">
            <ImageOff size={20} strokeWidth={1.5} />
            <span>Not yet generated</span>
          </div>
        ) : (
          <img
            src={src}
            alt={label}
            className="w-full h-full object-contain"
            onError={() => setErrored(true)}
            loading="lazy"
          />
        )}
      </div>
      <div className="px-4 py-3 flex items-center justify-between gap-3">
        <p className="text-[11px] uppercase tracking-wider text-[#476B6B]">{label}</p>
        {!errored && (
          <a
            href={src}
            download={downloadName}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#1A2424] hover:text-[#476B6B]"
            title="Download"
            aria-label="Download image"
          >
            <Download size={14} strokeWidth={1.6} />
          </a>
        )}
      </div>
    </div>
  );
}
