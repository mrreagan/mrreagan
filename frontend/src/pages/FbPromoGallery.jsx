/* FbPromoGallery — internal review page for the Facebook promo assets.
 *
 * URL: /fb-promo
 *
 * For each phrase shows:
 *   1. Hero shot (square 1080x1080)
 *   2. v2 social card (paraphrased explanation — earlier draft)
 *   3. v3 social card (VERBATIM "What this means" summary — original)
 *
 * Both v2 and v3 cards are 1080x1620 / 1080x1920 portrait, ready to drop
 * straight into the Facebook feed. Tap any image to open full resolution.
 */
import React from "react";
import { Download } from "lucide-react";

const ITEMS = [
  {
    idx: "01",
    slug: "secure-connection",
    phrase: "Secure connection is your birthright",
    vibe: "cream linen + dried lavender",
    v3Text: (
      <>
        This isn't aspirational. It's not "if you're lucky" or "for some
        people." It's the constitutional truth that every human being
        arrives wired for, and worthy of, a steady, responsive bond. We
        don't earn secure attachment — we recognize it as the default we
        were built for, even when life pulled us away from it. To carry
        this phrase is to refuse the lie that connection has to be
        deserved, performed, or paid for.
        <br /><br />
        <em className="text-[#1A2A33] not-italic">
          <span className="italic">You were born holding the deed.</span>
        </em>
      </>
    ),
  },
  {
    idx: "02",
    slug: "founder-of-love-story",
    phrase: "You are the founder of your own love story",
    vibe: "ivory deckle paper + olive leaf",
    v3Text: (
      <>
        Most of us inherited a love story before we could write one — from
        our parents' marriage, our family's silences, our culture's
        clichés about how romance is supposed to go. To be the founder is
        to take the pen back. Not to discard what was given, but to
        author the next chapter consciously: who you love, how you love,
        what counts as a happy ending.
        <br /><br />
        <em className="text-[#1A2A33]">
          The bond you build now isn't an extension of what came before —
          it's a fresh founding document, and you're the one signing it.
        </em>
      </>
    ),
  },
  {
    idx: "03",
    slug: "created-for-connection",
    phrase: "We are created for connection",
    vibe: "pale stone + rosemary in cream dish",
    v3Text: (
      <>
        This is Sue Johnson's discovery dressed as theology and biology
        at the same time. Whether you read "created" as a divine act or a
        developmental one, the message is identical: your nervous system
        was not designed to thrive alone. The hunger you feel for
        closeness isn't a personal failing or a sign of weakness — it's
        the original blueprint asserting itself.
        <br /><br />
        <em className="text-[#1A2A33]">
          We are not solitary creatures who occasionally bond. We are
          bonding creatures who occasionally find ourselves alone.
        </em>
      </>
    ),
  },
  {
    idx: "04",
    slug: "bond-is-the-cure",
    phrase: "The bond is the cure",
    vibe: "off-white raw silk + bronze key",
    v3Text: (
      <>
        We chase cures in books, therapy, podcasts, and prescriptions.
        Sometimes one of them helps. But the deepest healing for
        relational wounds always comes through a different relationship —
        one that proves the old story wrong by living a steadier one in
        its place. The bond itself, when it is finally safe and
        responsive, becomes the medicine.
        <br /><br />
        <em className="text-[#1A2A33]">
          Not a metaphor. Not a side effect. The cure.
        </em>
      </>
    ),
  },
  {
    idx: "05",
    slug: "repair-is-older",
    phrase: "Repair is older than rupture",
    vibe: "patch inside cream porcelain dish with gold kintsugi seams",
    v3Text: (
      <>
        Most people assume rupture comes first and repair is the scramble
        afterward. But mother-infant repair cycles begin in the first
        weeks of life — before any conscious wound is ever named. The
        dance of rupture-and-repair is the relationship; it's been native
        to you since before you had language for either.
        <br /><br />
        <em className="text-[#1A2A33]">
          You don't have to learn repair from scratch. You have to
          remember it.
        </em>
      </>
    ),
  },
];

const heroSrc = (it) => `/fb-assets/v4/hero-${it.idx}-${it.slug}.png`;
const v2Src = (it) => `/fb-assets/v2/fb-${it.idx}-${it.slug}.png`;
const v3Src = (it) => `/fb-assets/v3/fb-${it.idx}-${it.slug}.png`;
const v4Src = (it) => `/fb-assets/v4/fb-${it.idx}-${it.slug}.png`;
const v4lsSrc = (it) => `/fb-assets/v4-landscape/fb-ls-${it.idx}-${it.slug}.png`;
const igSqSrc = (it) => `/fb-assets/v4-multi/ig-sq-${it.idx}-${it.slug}.png`;
const igStorySrc = (it) => `/fb-assets/v4-multi/ig-story-${it.idx}-${it.slug}.png`;
const twSrc = (it) => `/fb-assets/v4-multi/tw-${it.idx}-${it.slug}.png`;

function Tile({ href, label, dims, alt, testid }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="group block"
      data-testid={testid}
    >
      <div className="relative bg-white/40 border border-[#E5DCC4] overflow-hidden">
        <img src={href} alt={alt} className="w-full h-auto block" loading="lazy" />
        <span className="absolute top-3 left-3 text-[10px] uppercase tracking-[0.18em] bg-[#F8F2E5]/95 text-[#2C4E5A] px-2 py-1">
          {label} · {dims}
        </span>
        <span className="absolute top-3 right-3 bg-white/90 border border-[#E5DCC4] rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition">
          <Download size={14} strokeWidth={1.6} className="text-[#2C4E5A]" />
        </span>
      </div>
    </a>
  );
}

export default function FbPromoGallery() {
  return (
    <div
      className="min-h-screen bg-[#F8F2E5]"
      data-testid="fb-promo-gallery-page"
    >
      <div className="max-w-5xl mx-auto px-5 py-10 sm:py-14">
        <header className="mb-10 sm:mb-14">
          <p className="text-xs uppercase tracking-[0.25em] text-[#A87A4A] mb-3">
            Internal review
          </p>
          <h1 className="text-3xl sm:text-4xl font-serif italic text-[#2C4E5A] leading-tight">
            Facebook promo assets
          </h1>
          <p className="text-sm text-[#3D6373] mt-3 max-w-2xl leading-relaxed">
            <strong>v4 landscape</strong> (1920×1080) is the canonical
            Facebook format. Multi-platform variants now live alongside it:{" "}
            <strong>Instagram square</strong> (1080×1080),{" "}
            <strong>Instagram Story / Reel</strong> (1080×1920), and{" "}
            <strong>Twitter / X</strong> (1600×900). v4 heroes use a 3/4
            perspective, alternating tilts, a signature object per phrase
            (signet ring · pen · paired cups · key · kintsugi dish) and
            softer lighting. Earlier portrait drafts (v2 paraphrased, v3
            verbatim) are tucked inside the "Show earlier drafts" toggle on
            each section. Tap any image to open full resolution.
          </p>
        </header>

        <div className="space-y-20">
          {ITEMS.map((it) => (
            <section
              key={it.idx}
              data-testid={`fb-promo-${it.idx}`}
              className="border-t border-[#E5DCC4] pt-10"
            >
              <div className="flex items-baseline justify-between mb-2 gap-4 flex-wrap">
                <h2 className="text-2xl sm:text-3xl font-serif italic text-[#2C4E5A] leading-snug">
                  {it.idx}. {it.phrase}
                </h2>
                <p className="text-xs uppercase tracking-[0.2em] text-[#A87A4A]">
                  {it.vibe}
                </p>
              </div>

              {/* ── Row 0 : v4 landscape (NEW — recommended) ─────────── */}
              <div className="mt-6">
                <Tile
                  href={v4lsSrc(it)}
                  label="v4 landscape — recommended"
                  dims="1920 × 1080"
                  alt={`v4 landscape — ${it.phrase}`}
                  testid={`fb-promo-${it.idx}-v4ls`}
                />
              </div>

              {/* ── Row A : Hero (v4) + v4 portrait card ─────────────── */}
              <div className="grid sm:grid-cols-2 gap-5 mt-5">
                <Tile
                  href={heroSrc(it)}
                  label="v4 hero — perspective + signature"
                  dims="1024 × 1024"
                  alt={`Hero — ${it.phrase}`}
                  testid={`fb-promo-${it.idx}-hero`}
                />
                <Tile
                  href={v4Src(it)}
                  label="v4 portrait card (Facebook)"
                  dims="1080 × 1920"
                  alt={`v4 portrait — ${it.phrase}`}
                  testid={`fb-promo-${it.idx}-v4`}
                />
              </div>

              {/* ── Row IG : Instagram square + Story/Reel ───────────── */}
              <div className="grid sm:grid-cols-2 gap-5 mt-5">
                <Tile
                  href={igSqSrc(it)}
                  label="Instagram square (feed)"
                  dims="1080 × 1080"
                  alt={`IG square — ${it.phrase}`}
                  testid={`fb-promo-${it.idx}-igsq`}
                />
                <Tile
                  href={igStorySrc(it)}
                  label="Instagram Story / Reel"
                  dims="1080 × 1920"
                  alt={`IG story — ${it.phrase}`}
                  testid={`fb-promo-${it.idx}-igstory`}
                />
              </div>

              {/* ── Row Twitter : single full-width tile ─────────────── */}
              <div className="mt-5">
                <Tile
                  href={twSrc(it)}
                  label="Twitter / X card"
                  dims="1600 × 900"
                  alt={`Twitter — ${it.phrase}`}
                  testid={`fb-promo-${it.idx}-tw`}
                />
              </div>

              {/* ── Row B : older v2 + v3 (kept for comparison) ──────── */}
              <details className="mt-5">
                <summary className="cursor-pointer text-xs uppercase tracking-[0.2em] text-[#A87A4A] py-2">
                  Show earlier drafts (v2 + v3)
                </summary>
                <div className="grid sm:grid-cols-2 gap-5 mt-3">
                  <Tile
                    href={v2Src(it)}
                    label="v2 card (paraphrased)"
                    dims="1080 × 1620"
                    alt={`v2 — ${it.phrase}`}
                    testid={`fb-promo-${it.idx}-v2`}
                  />
                  <Tile
                    href={v3Src(it)}
                    label="v3 card (verbatim)"
                    dims="1080 × 1920"
                    alt={`v3 — ${it.phrase}`}
                    testid={`fb-promo-${it.idx}-v3`}
                  />
                </div>
              </details>

              {/* ── Verbatim text typeset for reference ──────────────── */}
              <div className="mt-6 max-w-3xl">
                <p className="text-[11px] uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
                  What this means — verbatim
                </p>
                <p className="text-[#2C4E5A] text-base sm:text-[17px] leading-relaxed font-serif italic">
                  {it.v3Text}
                </p>
              </div>
            </section>
          ))}
        </div>

        <footer className="mt-20 pt-10 border-t border-[#E5DCC4] text-xs text-[#A87A4A] tracking-[0.2em] uppercase">
          birthright.live · internal preview
        </footer>
      </div>
    </div>
  );
}
