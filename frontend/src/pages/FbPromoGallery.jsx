/* FbPromoGallery — internal review page for the Facebook promo assets.
 *
 * URL: /fb-promo
 *
 * Shows all 5 hero shots + 5 social cards side-by-side per phrase so the
 * founder can preview them on any device (desktop or mobile) without
 * downloading. Click any image to open the full-resolution file in a new
 * tab. A single button per phrase lets you save both files.
 */
import React from "react";
import { Download } from "lucide-react";

const ITEMS = [
  {
    idx: "01",
    slug: "secure-connection",
    phrase: "Secure connection is your birthright",
    vibe: "cream linen + dried lavender",
    explanation: (
      <>
        Before you earned it, before you proved yourself worthy, before the
        world taught you to bargain for love — connection was already yours.
        A secure bond is not a reward for good behaviour. It is the
        inheritance every person is born holding.
        <br /><br />
        <em className="text-[#1A2A33]">
          To return to it is not to gain something new; it is to remember
          what you already are.
        </em>
      </>
    ),
  },
  {
    idx: "02",
    slug: "founder-of-love-story",
    phrase: "You are the founder of your own love story",
    vibe: "ivory deckle paper + olive leaf",
    explanation: (
      <>
        No one writes your story for you. Not the family you came from, not
        the wounds you carry, not the script the world handed you. You are
        the founder — the one who chooses, who repairs, who begins again.
        <br /><br />
        <em className="text-[#1A2A33]">The pen has always been in your hand.</em>
      </>
    ),
  },
  {
    idx: "03",
    slug: "created-for-connection",
    phrase: "We are created for connection",
    vibe: "pale stone + rosemary in cream dish",
    explanation: (
      <>
        Our nervous systems are not built for isolation. From the first
        breath, we calibrate ourselves through the eyes, voice and warmth
        of another. Loneliness is not a personality trait — it is a signal
        that we were designed for something more.
        <br /><br />
        <em className="text-[#1A2A33]">
          Connection is not optional. It is constitutive.
        </em>
      </>
    ),
  },
  {
    idx: "04",
    slug: "bond-is-the-cure",
    phrase: "The bond is the cure",
    vibe: "off-white raw silk + bronze key",
    explanation: (
      <>
        Insight will not heal you. Strategies will not heal you. A book, a
        podcast, a perfectly worded boundary — none of them will heal you.
        The bond heals you. The repeated experience of being seen, held,
        and stayed with by someone who will not leave — that is the
        medicine.
        <br /><br />
        <em className="text-[#1A2A33]">Everything else is the wrapper.</em>
      </>
    ),
  },
  {
    idx: "05",
    slug: "repair-is-older",
    phrase: "Repair is older than rupture",
    vibe: "patch inside cream porcelain dish with gold kintsugi seams",
    explanation: (
      <>
        Long before the first wound, repair was already inside us. Babies
        cry and reach. Parents return. The dance of rupture and repair is
        older than language, older than memory, older than the breach
        itself.
        <br /><br />
        <em className="text-[#1A2A33]">
          The capacity to mend is not something we acquire — it is
          something we are born holding, waiting for the moment we are
          brave enough to use it.
        </em>
      </>
    ),
  },
];

const heroSrc = (it) => `/fb-assets/v2/hero-${it.idx}-${it.slug}.png`;
const cardSrc = (it) => `/fb-assets/v2/fb-${it.idx}-${it.slug}.png`;

export default function FbPromoGallery() {
  return (
    <div
      className="min-h-screen bg-[#F8F2E5]"
      data-testid="fb-promo-gallery-page"
    >
      <div className="max-w-5xl mx-auto px-5 py-10 sm:py-14">
        <header className="mb-10 sm:mb-14">
          <p className="text-xs uppercase tracking-[0.25em] text-[#A87A4A] mb-3">
            Internal review · v2
          </p>
          <h1 className="text-3xl sm:text-4xl font-serif italic text-[#2C4E5A] leading-tight">
            Facebook promo assets
          </h1>
          <p className="text-sm text-[#3D6373] mt-3 max-w-xl">
            Five phrases × two assets each. Hero shots (square, 1080×1080)
            for stand-alone posts; portrait cards (1080×1620) ready to drop
            into the Facebook feed. Tap any image to open full resolution.
          </p>
        </header>

        <div className="space-y-16 sm:space-y-20">
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

              <div className="grid sm:grid-cols-2 gap-5 mt-6">
                <a
                  href={heroSrc(it)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group block"
                  data-testid={`fb-promo-${it.idx}-hero`}
                >
                  <div className="relative bg-white/40 border border-[#E5DCC4] overflow-hidden">
                    <img
                      src={heroSrc(it)}
                      alt={`Hero — ${it.phrase}`}
                      className="w-full h-auto block"
                      loading="lazy"
                    />
                    <span className="absolute top-3 left-3 text-[10px] uppercase tracking-[0.18em] bg-[#F8F2E5]/95 text-[#2C4E5A] px-2 py-1">
                      Hero · 1080 × 1080
                    </span>
                    <span className="absolute top-3 right-3 bg-white/90 border border-[#E5DCC4] rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition">
                      <Download size={14} strokeWidth={1.6} className="text-[#2C4E5A]" />
                    </span>
                  </div>
                </a>

                <a
                  href={cardSrc(it)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group block"
                  data-testid={`fb-promo-${it.idx}-card`}
                >
                  <div className="relative bg-white/40 border border-[#E5DCC4] overflow-hidden">
                    <img
                      src={cardSrc(it)}
                      alt={`Social card — ${it.phrase}`}
                      className="w-full h-auto block"
                      loading="lazy"
                    />
                    <span className="absolute top-3 left-3 text-[10px] uppercase tracking-[0.18em] bg-[#F8F2E5]/95 text-[#2C4E5A] px-2 py-1">
                      Card · 1080 × 1620
                    </span>
                    <span className="absolute top-3 right-3 bg-white/90 border border-[#E5DCC4] rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition">
                      <Download size={14} strokeWidth={1.6} className="text-[#2C4E5A]" />
                    </span>
                  </div>
                </a>
              </div>

              <div className="mt-6 max-w-2xl">
                <p className="text-[#3D6373] text-base sm:text-lg leading-relaxed font-serif">
                  {it.explanation}
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
