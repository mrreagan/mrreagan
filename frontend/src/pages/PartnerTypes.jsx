import React from "react";
import { Link } from "react-router-dom";
import { Users, Heart, Microscope, ShoppingBag, Palette, MapPin } from "lucide-react";

const TYPES = [
  {
    slug: "facilitator", icon: Users, color: "text-[#9E3C3C]",
    label: "Facilitator",
    one_liner: "You lead Birthright workshops, retreats, or classes in your community.",
    foundation_benefit: "Trained practitioners extend the work into new geographies.",
    partner_benefit: "Workshop listing, registration, materials access, gathering tools, payouts via revenue share.",
    financial: { rate: "Up to 65%", basis: "Birthright-IP workshop revenue", notes: "Off-site sales attributed via referral codes earn 25% by default." },
    mission_alignment: "Be a quiet, secure, skillful presence for participants doing the work.",
  },
  {
    slug: "community", icon: Heart, color: "text-[#476B6B]",
    label: "Community",
    one_liner: "You're an organization or community that brings the work to your audience.",
    foundation_benefit: "Trusted introductions to whole communities — congregations, schools, recovery groups.",
    partner_benefit: "Organization profile, group rates, referral attribution, optional steward role for a geographic node.",
    financial: { rate: "25%", basis: "Referred registrations + sales", notes: "Payouts monthly when balance exceeds $50." },
    mission_alignment: "Steward the work as it enters your community. No gatekeeping; many doors.",
  },
  {
    slug: "research", icon: Microscope, color: "text-[#3F4A8C]",
    label: "Research",
    one_liner: "You publish briefs, papers, or studies relevant to secure attachment + presence work.",
    foundation_benefit: "Keeps the work intellectually honest. Builds the evidence base.",
    partner_benefit: "Research profile, AI Research Collaborator credits, archive of your published artifacts.",
    financial: { rate: "0% direct; promotion fees", basis: "Optional Birthright-funded promotion of your work", notes: "Honoraria available for invited papers." },
    mission_alignment: "Make the work knowable. Citations welcome, conjecture marked.",
  },
  {
    slug: "vendor", icon: ShoppingBag, color: "text-[#9E6C2C]",
    label: "Vendor",
    one_liner: "You make physical or digital goods (merch, books, journals, prints) we list in the shop.",
    foundation_benefit: "Goods carry the work into daily life — what people hold, wear, write in.",
    partner_benefit: "Storefront listing, AI Studio for product design, Printful + Lulu POD fulfillment, vendor PDM AI.",
    financial: { rate: "Variable", basis: "Per-product split set at listing", notes: "Founding partners earn an additional 5% for 5 years." },
    mission_alignment: "Make beautiful, durable, honestly-priced things.",
  },
  {
    slug: "artist", icon: Palette, color: "text-[#9E3C3C]",
    label: "Artist",
    one_liner: "You're a painter, photographer, sculptor, musician, ceramicist, or other maker — practice as presence.",
    foundation_benefit: "Beauty as part of the experience. Artists are co-stewards of the room.",
    partner_benefit: "Curated Gallery space, audio/video intro, collections, commission inquiries, performance schedule, your own gallery URL.",
    financial: { rate: "20% added at checkout (not deducted)", basis: "Buyer pays artist's full list price + 20% foundation gift", notes: "Buyer sees the math. Optional: artist absorbs markup or donates proceeds." },
    mission_alignment: "Make space for makers and creators who are more than just product salesmen.",
  },
  {
    slug: "steward", icon: MapPin, color: "text-[#01784E]",
    label: "Steward",
    one_liner: "You host and moderate one local community node in Gather — a city or neighborhood.",
    foundation_benefit: "Local presence that the foundation can't manufacture from afar.",
    partner_benefit: "Curate your local Gather page, welcome new neighbors, moderate the message board, pin local events, host quarterly calls.",
    financial: { rate: "0%", basis: "Service role — equity in mission", notes: "If revenue transacts in your community (workshop signups, artist sales), the foundation takes a standard cut; you're recognized but not paid out." },
    mission_alignment: "Tend the room. Welcome people in. Hold the standard quietly.",
  },
];

export default function PartnerTypes() {
  return (
    <div className="container-page py-12" data-testid="partner-types-page">
      <span className="label">Partner</span>
      <h1 className="editorial-h1 mt-2">Ways to partner with Birthright</h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Six honest ways to be in this with us. Each row below shows what you bring,
        what we give, what the money looks like (if any), and how it lines up with mission.
        Most partners are one type. Some hold two.
      </p>

      <div className="overflow-x-auto mt-8" data-testid="partner-types-table">
        <table className="min-w-full text-sm border-collapse">
          <thead>
            <tr className="border-b-2 border-[#0F2424] text-left">
              <th className="py-2 pr-4 font-serif text-base">Type</th>
              <th className="py-2 pr-4 font-serif text-base">What you do</th>
              <th className="py-2 pr-4 font-serif text-base">Foundation gets</th>
              <th className="py-2 pr-4 font-serif text-base">You get</th>
              <th className="py-2 pr-4 font-serif text-base">Money</th>
              <th className="py-2 font-serif text-base">Mission alignment</th>
            </tr>
          </thead>
          <tbody>
            {TYPES.map((t) => {
              const Icon = t.icon;
              return (
                <tr key={t.slug} className="border-b border-[#E5E1D8] align-top" data-testid={`partner-type-row-${t.slug}`}>
                  <td className="py-4 pr-4">
                    <div className="flex items-center gap-2">
                      <Icon size={18} strokeWidth={1.4} className={t.color} />
                      <span className="font-serif text-lg">{t.label}</span>
                    </div>
                  </td>
                  <td className="py-4 pr-4 text-[#5C6B6B] max-w-[280px]">{t.one_liner}</td>
                  <td className="py-4 pr-4 text-[#5C6B6B] max-w-[260px]">{t.foundation_benefit}</td>
                  <td className="py-4 pr-4 text-[#5C6B6B] max-w-[280px]">{t.partner_benefit}</td>
                  <td className="py-4 pr-4 text-[#5C6B6B] max-w-[240px]">
                    <p className="font-medium text-[#0F2424]" data-testid={`partner-type-rate-${t.slug}`}>{t.financial.rate}</p>
                    <p className="text-xs mt-1">{t.financial.basis}</p>
                    <p className="text-[10px] text-[#476B6B] mt-1 italic">{t.financial.notes}</p>
                  </td>
                  <td className="py-4 text-[#5C6B6B] italic max-w-[260px]">{t.mission_alignment}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-8 max-w-2xl space-y-3">
        <p className="text-sm text-[#5C6B6B]">
          Ready to apply? Pick the type that fits — and don't worry if you fit more than one.
          Each application is reviewed by a board member.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link to="/partner/apply" className="btn-primary text-sm" data-testid="partner-types-apply-btn">Apply</Link>
          <Link to="/partner" className="btn-outline text-sm" data-testid="partner-types-directory-btn">Browse current partners</Link>
        </div>
      </div>
    </div>
  );
}
