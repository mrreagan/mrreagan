/* PatchesLanding — public conversion page for the Foundation patch series.
 *
 * URL: /shop/patches  (also pinged from FB ads)
 *
 * Five engraved attachment-theory phrases. Foundation does not produce
 * these — fulfillment is routed to 7C's Farmstead (the artisan who
 * crafted the original samples). Their custom-order page accepts the
 * specification + buyer's shipping address; we keep a 20% Foundation
 * patronage markup on top of their list price, same as the gallery
 * artist patronage flow.
 *
 * IN THIS VERSION: we lay out the five phrases with their hero images
 * and explanations, and the primary CTA links to the fulfillment
 * partner's custom-order intake page. When the storefront SKU is
 * actually live, the CTA can flip to /equip/{slug} for direct checkout.
 */
import React from "react";
import { ArrowUpRight, Sparkles, Heart, ExternalLink } from "lucide-react";

const FULFILLMENT_URL = "https://7csfarmstead.com/pages/custom-order";
const FULFILLMENT_NAME = "7C's Farmstead";

const PHRASES = [
  {
    idx: "01", slug: "secure-connection",
    phrase: "Secure connection is your birthright",
    focal: "birthright",
    explanation: (
      <>
        This isn&apos;t aspirational. It&apos;s the constitutional truth that every human being arrives wired for, and worthy of, a steady, responsive bond. We don&apos;t earn secure attachment — we recognize it as the default we were built for.
        <br /><br />
        <em>You were born holding the deed.</em>
      </>
    ),
  },
  {
    idx: "02", slug: "founder-of-love-story",
    phrase: "You are the founder of your own love story",
    focal: "founder",
    explanation: (
      <>
        Most of us inherited a love story before we could write one. To be the founder is to take the pen back — to author the next chapter consciously: who you love, how you love, what counts as a happy ending.
        <br /><br />
        <em>The pen has always been in your hand.</em>
      </>
    ),
  },
  {
    idx: "03", slug: "created-for-connection",
    phrase: "We are created for connection",
    focal: "connection",
    explanation: (
      <>
        Whether you read &ldquo;created&rdquo; as a divine act or a developmental one, the message is identical: your nervous system was not designed to thrive alone. The hunger you feel for closeness is the original blueprint asserting itself.
        <br /><br />
        <em>We are bonding creatures who occasionally find ourselves alone.</em>
      </>
    ),
  },
  {
    idx: "04", slug: "bond-is-the-cure",
    phrase: "The bond is the cure",
    focal: "cure",
    explanation: (
      <>
        We chase cures in books, therapy, podcasts, prescriptions. But the deepest healing for relational wounds always comes through a different relationship — one that proves the old story wrong by living a steadier one in its place.
        <br /><br />
        <em>Not a metaphor. Not a side effect. The cure.</em>
      </>
    ),
  },
  {
    idx: "05", slug: "repair-is-older",
    phrase: "Repair is older than rupture",
    focal: "Repair",
    explanation: (
      <>
        Mother-infant repair cycles begin in the first weeks of life — before any conscious wound is ever named. The dance of rupture-and-repair is the relationship; it&apos;s been native to you since before you had language for either.
        <br /><br />
        <em>You don&apos;t have to learn repair from scratch. You have to remember it.</em>
      </>
    ),
  },
];

export default function PatchesLanding() {
  return (
    <div className="min-h-screen bg-[#F8F2E5]" data-testid="patches-landing">
      <div className="max-w-5xl mx-auto px-5 py-12 sm:py-16">

        <header className="mb-14 sm:mb-20 text-center">
          <p className="text-xs uppercase tracking-[0.25em] text-[#A87A4A] mb-3">
            Foundation collection · leather engraving
          </p>
          <h1 className="text-3xl sm:text-5xl font-serif italic text-[#2C4E5A] leading-tight">
            Five phrases<br />you can carry in your hand.
          </h1>
          <p className="text-base sm:text-lg text-[#3D6373] mt-5 leading-relaxed font-serif italic max-w-xl mx-auto">
            Hand-engraved leather patches carrying the attachment-theory
            statements at the heart of birthright&apos;s work. Crafted in
            small batches by an artisan partner. Every order supports
            Foundation patronage and the artist&apos;s livelihood — no
            mass production, no middleman markup.
          </p>
          <a
            href={FULFILLMENT_URL}
            target="_blank"
            rel="noreferrer noopener"
            data-testid="patches-cta-top"
            className="inline-flex items-center gap-2 mt-7 px-6 py-3 bg-[#2C4E5A] text-[#F8F2E5] text-sm uppercase tracking-[0.18em] hover:bg-[#1F3942] transition"
          >
            <Sparkles size={14} strokeWidth={1.6} />
            Order through {FULFILLMENT_NAME}
            <ExternalLink size={14} strokeWidth={1.6} />
          </a>
        </header>

        <section className="space-y-20">
          {PHRASES.map((p) => (
            <article
              key={p.idx}
              className="grid sm:grid-cols-2 gap-6 sm:gap-10 items-center"
              data-testid={`patches-phrase-${p.idx}`}
            >
              <div className={p.idx % 2 === 0 ? "sm:order-2" : ""}>
                <div className="relative bg-white/40 border border-[#E5DCC4] overflow-hidden">
                  <img
                    src={`/fb-assets/v4/hero-${p.idx}-${p.slug}.png`}
                    alt={p.phrase}
                    className="w-full h-auto block"
                    loading="lazy"
                  />
                  <span className="absolute top-3 left-3 text-[10px] uppercase tracking-[0.2em] bg-[#F8F2E5]/95 text-[#2C4E5A] px-2 py-1">
                    {p.idx}
                  </span>
                </div>
              </div>
              <div>
                <h2 className="text-2xl sm:text-3xl font-serif italic text-[#2C4E5A] leading-snug">
                  {p.phrase}
                </h2>
                <p className="text-[#3D6373] text-base sm:text-[17px] leading-relaxed font-serif italic mt-4">
                  {p.explanation}
                </p>
              </div>
            </article>
          ))}
        </section>

        {/* HOW IT WORKS ─────────────────────────────────────────────── */}
        <section className="mt-24 border-t border-[#E5DCC4] pt-12" data-testid="patches-how">
          <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3 text-center">
            How ordering works
          </p>
          <div className="grid sm:grid-cols-3 gap-8 mt-6">
            <div>
              <p className="font-serif italic text-xl text-[#2C4E5A]">1. Choose</p>
              <p className="text-[#3D6373] text-sm mt-2 font-serif italic leading-relaxed">
                Pick one or more of the five phrases. Specify leather
                colour, size, and any personalisation in the custom-order
                form.
              </p>
            </div>
            <div>
              <p className="font-serif italic text-xl text-[#2C4E5A]">2. Craft</p>
              <p className="text-[#3D6373] text-sm mt-2 font-serif italic leading-relaxed">
                {FULFILLMENT_NAME} hand-engraves each piece in small
                batches. Lead time is typically 2&ndash;4 weeks.
              </p>
            </div>
            <div>
              <p className="font-serif italic text-xl text-[#2C4E5A]">3. Support</p>
              <p className="text-[#3D6373] text-sm mt-2 font-serif italic leading-relaxed">
                A 20% Foundation patronage rests on top of the list
                price — funding workshops, research, and the gallery&apos;s artist patronage flow.
              </p>
            </div>
          </div>
        </section>

        {/* PARTNER ATTRIBUTION ─────────────────────────────────────── */}
        <section className="mt-20 border-t border-[#E5DCC4] pt-10" data-testid="patches-partner">
          <div className="flex items-start gap-4">
            <Heart size={20} strokeWidth={1.6} className="text-[#A87A4A] shrink-0 mt-1" />
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A]">
                Fulfilment partner
              </p>
              <h3 className="text-xl font-serif italic text-[#2C4E5A] mt-1">
                {FULFILLMENT_NAME}
              </h3>
              <p className="text-[#3D6373] text-sm mt-2 font-serif italic leading-relaxed max-w-2xl">
                birthright Foundation does not produce these patches.
                Fulfilment is handled by {FULFILLMENT_NAME}, the artisan
                who crafted the original sample series. Ordering through
                them keeps the work in the hands of the maker.
              </p>
              <a
                href={FULFILLMENT_URL}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-1 mt-3 text-sm text-[#2C4E5A] hover:underline font-serif italic"
              >
                Visit their custom-order page
                <ArrowUpRight size={14} strokeWidth={1.6} />
              </a>
            </div>
          </div>
        </section>

        {/* BOTTOM CTA ─────────────────────────────────────────────── */}
        <section className="mt-20 text-center">
          <a
            href={FULFILLMENT_URL}
            target="_blank"
            rel="noreferrer noopener"
            data-testid="patches-cta-bottom"
            className="inline-flex items-center gap-2 px-6 py-3 bg-[#2C4E5A] text-[#F8F2E5] text-sm uppercase tracking-[0.18em] hover:bg-[#1F3942] transition"
          >
            <Sparkles size={14} strokeWidth={1.6} />
            Start your order
            <ExternalLink size={14} strokeWidth={1.6} />
          </a>
          <p className="text-xs text-[#5C6B6B] italic mt-4">
            Opens {FULFILLMENT_NAME}&apos;s secure custom-order intake form.
          </p>
        </section>

        <footer className="mt-20 pt-10 border-t border-[#E5DCC4] text-xs text-[#A87A4A] tracking-[0.2em] uppercase text-center">
          birthright.live · five phrases · five tiers · one community
        </footer>
      </div>
    </div>
  );
}
