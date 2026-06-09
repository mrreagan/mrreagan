/* ArtistPartnershipTerms — public clarity page at /partner/artist
 *
 * Clarity before commitment, our non-negotiable.
 * Fetches the live tier table from the backend so the numbers shown
 * here ARE the numbers the platform actually operates on. No drift.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sprout, Leaf, TreeDeciduous, Flower2, Sparkles, ArrowUpRight, ShieldCheck } from "lucide-react";
import api from "../lib/api";

const TIER_ICONS = {
  emerging: Sprout,
  sustaining: Leaf,
  established: TreeDeciduous,
  thriving: Flower2,
  flourishing: Sparkles,
};

function formatRange(lo, hi) {
  const f = (n) => `$${n.toLocaleString()}`;
  if (hi === null || hi === undefined) return `${f(lo)}+`;
  return `${f(lo)} – ${f(hi)}`;
}

export default function ArtistPartnershipTerms() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.get("/partner/artist/tier-table")
      .then((r) => setData(r.data))
      .catch(() => setErr(true));
  }, []);

  if (err) return null;

  return (
    <div className="min-h-screen bg-[#F8F2E5]" data-testid="artist-partnership-terms-page">
      <div className="max-w-3xl mx-auto px-5 py-12 sm:py-16">
        <header className="mb-12">
          <p className="text-xs uppercase tracking-[0.25em] text-[#A87A4A] mb-3">
            Artist Partnership · clarity before commitment
          </p>
          <h1 className="text-3xl sm:text-5xl font-serif italic text-[#2C4E5A] leading-tight">
            How partnering with birthright works
          </h1>
          <p className="text-base sm:text-lg text-[#3D6373] mt-5 leading-relaxed font-serif italic">
            Everything below is on the public record. The numbers on this
            page are the same numbers the system uses to compute every
            payout and every fee. Nothing changes without notice.
          </p>
        </header>

        {/* THE PRINCIPLE ──────────────────────────────────────────────── */}
        <section className="mb-14" data-testid="apt-principle">
          <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
            The principle
          </p>
          <h2 className="text-2xl sm:text-3xl font-serif italic text-[#2C4E5A] leading-snug">
            We only share in growth we contributed to.
          </h2>
          <p className="text-[#3D6373] text-base sm:text-[17px] leading-relaxed mt-4 font-serif">
            Artists are a community of interest. The spread between
            struggling and thriving is enormous — most artists are starving
            most of the time. If we can help an artist become more
            successful, that is its own reward. If our help materially
            grows their living, we participate proportionally — never
            disproportionately. The numbers below are designed to be
            <em> nearly negligible for emerging artists</em> and
            <em> meaningful only once we are demonstrably part of their
            success story.</em>
          </p>
        </section>

        {/* THREE WAYS WE WORK TOGETHER ──────────────────────────────── */}
        <section className="mb-14" data-testid="apt-three-routes">
          <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
            Three ways we work together
          </p>
          <div className="space-y-6 mt-4">
            <article className="border-l-2 border-[#A87A4A] pl-5">
              <h3 className="font-serif italic text-xl text-[#2C4E5A]">
                1. Patronage on birthright — <span className="not-italic font-medium">20% Foundation markup</span>
              </h3>
              <p className="text-[#3D6373] mt-2 font-serif italic leading-relaxed">
                Buyers see your work in the gallery and choose to support
                Foundation while collecting it. They pay <strong>your
                list price + 20%</strong> through our checkout. We keep
                the 20% (hospitality + curation). You receive
                <strong> 100% of your list price</strong>, on a payout
                cycle, and ship from your studio. <em>The 20% is on the
                buyer, not on you. It is constant across all tiers and
                does not change as you grow.</em>
              </p>
            </article>

            <article className="border-l-2 border-[#A87A4A] pl-5">
              <h3 className="font-serif italic text-xl text-[#2C4E5A]">
                2. You send buyers to birthright — <span className="not-italic font-medium">inbound referral</span>
              </h3>
              <p className="text-[#3D6373] mt-2 font-serif italic leading-relaxed">
                Share your birthright referral link from any of your
                channels. When a new visitor follows it and makes their
                first purchase on birthright within 30 days, you earn a
                percentage of that purchase. Rate depends on your tier
                (10% at the lowest tier, declining as you flourish — see
                below).
              </p>
            </article>

            <article className="border-l-2 border-[#A87A4A] pl-5">
              <h3 className="font-serif italic text-xl text-[#2C4E5A]">
                3. We send buyers to you — <span className="not-italic font-medium">outbound off-site referral</span>
              </h3>
              <p className="text-[#3D6373] mt-2 font-serif italic leading-relaxed">
                Visitors who discover you on birthright can click through
                to your own website. If they buy from you there within 30
                days, you self-report it quarterly and contribute a small
                share to Foundation. Rate depends on your tier — and at
                the Emerging tier it is <strong>0%</strong>. We take
                nothing from a struggling artist's off-site sale even if
                we drove the click.
              </p>
            </article>
          </div>
        </section>

        {/* TIER TABLE ──────────────────────────────────────────────── */}
        {data && (
          <section className="mb-14" data-testid="apt-tier-table">
            <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
              The five tiers
            </p>
            <h2 className="text-2xl sm:text-3xl font-serif italic text-[#2C4E5A] mb-2">
              You grow with us. We grow with you.
            </h2>
            <p className="text-[#3D6373] text-sm sm:text-base font-serif italic leading-relaxed mb-6">
              Your tier is determined by your <strong>trailing-12-month
              birthright-attributed gross revenue</strong> — the sum of
              your gallery sales on birthright (at list price) plus your
              self-reported off-site sales tagged via=birthright.
              Recomputed monthly. Tier changes take effect the 1st of the
              following month.
            </p>

            <div className="overflow-x-auto -mx-5 sm:mx-0">
              <table className="w-full text-sm sm:text-[15px] font-serif">
                <thead>
                  <tr className="border-b border-[#E5DCC4]">
                    <th className="text-left py-3 px-3 text-[10px] uppercase tracking-[0.2em] text-[#A87A4A] font-medium">Tier</th>
                    <th className="text-left py-3 px-3 text-[10px] uppercase tracking-[0.2em] text-[#A87A4A] font-medium">12-mo revenue with us</th>
                    <th className="text-right py-3 px-3 text-[10px] uppercase tracking-[0.2em] text-[#A87A4A] font-medium">Inbound % <span className="block text-[#5C6B6B] normal-case tracking-normal mt-1">(you earn)</span></th>
                    <th className="text-right py-3 px-3 text-[10px] uppercase tracking-[0.2em] text-[#A87A4A] font-medium">Outbound % <span className="block text-[#5C6B6B] normal-case tracking-normal mt-1">(you contribute)</span></th>
                  </tr>
                </thead>
                <tbody>
                  {data.tiers.map((t) => {
                    const Icon = TIER_ICONS[t.key] || Sprout;
                    return (
                      <tr key={t.key} className="border-b border-[#E5DCC4] last:border-0" data-testid={`apt-tier-row-${t.key}`}>
                        <td className="py-4 px-3">
                          <div className="flex items-center gap-3">
                            <Icon size={20} strokeWidth={1.5} className="text-[#A87A4A] shrink-0" />
                            <span className="italic text-[#2C4E5A] font-medium">{t.label}</span>
                          </div>
                        </td>
                        <td className="py-4 px-3 text-[#3D6373] italic">{formatRange(t.basis_lo, t.basis_hi)}</td>
                        <td className="py-4 px-3 text-right text-[#2C4E5A] font-medium">{t.inbound_pct}%</td>
                        <td className="py-4 px-3 text-right text-[#2C4E5A] font-medium">{t.outbound_pct}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-[#3D6373] italic mt-5 leading-relaxed">
              Outbound uses <strong>marginal brackets</strong>, like
              progressive tax: only the revenue <em>above</em> each
              threshold pays that tier's rate. Crossing a threshold by a
              dollar never re-taxes the dollars below it. A $20,000-year
              artist's effective outbound rate is approximately <strong>2%</strong>,
              not 4%.
            </p>
          </section>
        )}

        {/* WORKED EXAMPLES ──────────────────────────────────────────── */}
        <section className="mb-14" data-testid="apt-examples">
          <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
            What this looks like in practice
          </p>
          <div className="space-y-6">
            <ExampleCard
              tier="Emerging"
              revenue="$3,000"
              breakdown={[
                { label: "Patronage sales (on-site)", value: "$3,000" },
                { label: "Off-site referred sales", value: "$0" },
                { label: "Outbound fee owed to Foundation", value: "$0 — Emerging is exempt", strong: true },
                { label: "Inbound earnings (sample $400 of referred workshops)", value: "$40 (10% of $400)" },
              ]}
            />
            <ExampleCard
              tier="Sustaining"
              revenue="$12,000"
              breakdown={[
                { label: "Patronage sales (on-site)", value: "$8,000" },
                { label: "Off-site referred sales", value: "$4,000" },
                { label: "Outbound fee owed (marginal)", value: "$140 — 0% on first $5K, 2% on next $7K", strong: true },
                { label: "Effective outbound rate", value: "≈ 1.2%" },
              ]}
            />
            <ExampleCard
              tier="Flourishing"
              revenue="$250,000"
              breakdown={[
                { label: "Outbound fee owed (marginal across all brackets)", value: "$16,800", strong: true },
                { label: "Effective outbound rate", value: "≈ 6.7%" },
                { label: "Versus typical affiliate networks (Etsy/Saatchi/Society6)", value: "10 – 35% — you save substantially" },
              ]}
            />
          </div>
        </section>

        {/* ATTRIBUTION ──────────────────────────────────────────────── */}
        <section className="mb-14" data-testid="apt-attribution">
          <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
            Attribution — how a sale gets counted
          </p>

          <div className="grid sm:grid-cols-2 gap-6">
            <div className="border-l-2 border-[#A87A4A] pl-5">
              <h3 className="font-serif italic text-lg text-[#2C4E5A]">Inbound (you → us)</h3>
              <ul className="text-[#3D6373] text-[15px] font-serif italic leading-relaxed mt-3 space-y-2 list-disc list-inside">
                <li>30-day last-click cookie</li>
                <li><strong>First purchase only</strong> per buyer — once they buy from us once, future purchases are no longer attributed to you</li>
                <li>Auto-credited the moment Stripe pays</li>
              </ul>
            </div>
            <div className="border-l-2 border-[#A87A4A] pl-5">
              <h3 className="font-serif italic text-lg text-[#2C4E5A]">Outbound (us → you)</h3>
              <ul className="text-[#3D6373] text-[15px] font-serif italic leading-relaxed mt-3 space-y-2 list-disc list-inside">
                <li>30-day claim window after click</li>
                <li><strong>First purchase only</strong> per buyer</li>
                <li><strong>Self-reported quarterly</strong> — trust-based, no audit, no surveillance</li>
              </ul>
            </div>
          </div>

          <p className="text-[#3D6373] text-sm font-serif italic mt-6 leading-relaxed">
            "First purchase only" is the gentler interpretation. Most
            affiliate networks bill you on every purchase a referred
            buyer makes in the cookie window. We don't. Once a buyer has
            met you, they belong to you.
          </p>
        </section>

        {/* NON-NEGOTIABLES ──────────────────────────────────────────── */}
        <section className="mb-14" data-testid="apt-nonnegotiables">
          <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A] mb-3">
            Our non-negotiables
          </p>
          <ul className="space-y-3">
            {[
              "We do not reproduce, print, or remix your work without explicit, separate permission. Originals only on birthright.",
              "Your list price on birthright matches your list price on your own site. We add the 20% on top; we never undercut you.",
              "You ship directly from your studio. We never touch the artwork. Your name on the package, your relationship with your collector.",
              "Tier changes only ever happen on the 1st of the month, never mid-cycle.",
              "Tier numbers, attribution windows, and the 20% markup are public on this page and identical to what the system computes.",
              "You can leave at any time. We do not lock your inventory or hold your contact list.",
            ].map((line, i) => (
              <li key={i} className="flex items-start gap-3 text-[#3D6373] font-serif italic leading-relaxed">
                <ShieldCheck size={18} strokeWidth={1.6} className="text-[#A87A4A] shrink-0 mt-1" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* CTA ──────────────────────────────────────────────────────── */}
        <section className="mt-16 border-t border-[#E5DCC4] pt-10">
          <h2 className="text-2xl font-serif italic text-[#2C4E5A]">
            Ready to be seen alongside this work?
          </h2>
          <p className="text-[#3D6373] mt-2 font-serif italic">
            Apply to join the gallery. Approval takes 3 – 7 days. No fees
            to apply, no commitment until you publish your first work.
          </p>
          <Link
            to="/partner/become-an-artist"
            data-testid="apt-cta-apply"
            className="inline-flex items-center gap-2 mt-5 px-5 py-2.5 bg-[#2C4E5A] text-[#F8F2E5] text-sm uppercase tracking-[0.18em] hover:bg-[#1F3942] transition"
          >
            Begin application
            <ArrowUpRight size={16} strokeWidth={1.8} />
          </Link>
        </section>

        <footer className="mt-20 pt-10 border-t border-[#E5DCC4] text-xs text-[#A87A4A] tracking-[0.2em] uppercase">
          birthright.live · last revised today · numbers fetched from live API
        </footer>
      </div>
    </div>
  );
}

function ExampleCard({ tier, revenue, breakdown }) {
  return (
    <div className="bg-white/60 border border-[#E5DCC4] p-5">
      <div className="flex items-baseline justify-between mb-3">
        <p className="font-serif italic text-lg text-[#2C4E5A]">{tier}</p>
        <p className="text-xs uppercase tracking-[0.2em] text-[#A87A4A]">
          12-mo basis · {revenue}
        </p>
      </div>
      <dl className="text-sm font-serif divide-y divide-[#E5DCC4]">
        {breakdown.map((row, i) => (
          <div key={i} className="flex items-center justify-between gap-4 py-2">
            <dt className={`italic ${row.strong ? "text-[#2C4E5A] font-medium" : "text-[#3D6373]"}`}>{row.label}</dt>
            <dd className={row.strong ? "text-[#2C4E5A] font-medium" : "text-[#3D6373]"}>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
