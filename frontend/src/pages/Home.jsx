import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { ArrowRight, Calendar, Users, Flame, Sparkles, Heart, ShoppingBag } from "lucide-react";
import { NewsletterSignup } from "../components/Newsletter";
import { TaxStatusPill, FeaturedCampaignCard } from "../components/campaigns/CampaignParts";
import FirstDollarWall from "../components/home/FirstDollarWall";

const HERO_BG = "https://static.prod-images.emergentagent.com/jobs/c61b4345-eef4-4783-a5af-85e8af10eaf3/images/10154eafef8a2623b8b4e86a0d0a8065334110989eba28a8c99077e78f19d1fa.png";
const COMMUNITY_IMG_1 = "https://images.unsplash.com/photo-1634155938686-24a26c55d71a?w=1200";

const formatDate = (iso) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
};

const HOW_IT_WORKS = [
  { n: "01", title: "Foundations", body: "Begin here. Learn the language and felt-sense of secure bonds in a weekend immersion." },
  { n: "02", title: "Practice", body: "Live skills work with certified facilitators. Smaller cohorts. Deeper application." },
  { n: "03", title: "Living the Work", body: "An ongoing peer community. Monthly circles. The practice in real life." },
];

// ---------- Hero ----------
function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <img src={HERO_BG} alt="" className="w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#FAF8F5]/60 via-[#FAF8F5]/85 to-[#FAF8F5]" />
      </div>
      <div className="container-page pt-20 pb-24 lg:pt-32 lg:pb-32">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-end">
          <div className="lg:col-span-7 fade-up">
            <span className="label" data-testid="hero-label">A foundation for connection</span>
            <h1 className="editorial-h1 mt-5">
              Secure bonds<br />
              <span className="italic text-[#476B6B]">are your birthright.</span>
            </h1>
            <p className="mt-7 text-lg text-[#5C6B6B] max-w-xl leading-relaxed">
              Workshops, materials, and a quiet community for everyone learning to claim and recover the relationships they were always meant to have.
            </p>
            <div className="mt-9 flex flex-wrap gap-3" data-testid="hero-cta">
              <Link to="/practice" className="btn-primary" data-testid="hero-browse-workshops">
                Browse workshops <ArrowRight size={16} strokeWidth={1.5} />
              </Link>
              <Link to="/mission" className="btn-outline">
                Read our mission
              </Link>
            </div>
          </div>
          <div className="lg:col-span-5 fade-up-delay-1">
            <div className="relative">
              <img
                src={COMMUNITY_IMG_1}
                alt="Workshop circle"
                className="rounded-2xl w-full aspect-[4/5] object-cover float-anim"
              />
              <div className="absolute -bottom-6 -left-6 card p-5 max-w-[200px] hidden md:block">
                <Flame size={22} strokeWidth={1.5} className="text-[#C9A961]" />
                <p className="text-sm font-medium mt-2">Secure Bonds &gt; Thrive</p>
                <p className="text-xs text-[#5C6B6B] mt-1">The practice ground for the relationships you want.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------- Mission strip ----------
function MissionStrip() {
  return (
    <section className="border-y border-[#E5E1D8] bg-white">
      <div className="container-page py-14 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          <div className="lg:col-span-4">
            <span className="label">Our mission</span>
            <p className="editorial-h2 mt-3">We are<br />the practice ground.</p>
          </div>
          <div className="lg:col-span-8">
            <p className="text-lg text-[#1A2424] leading-relaxed">
              We exist to empower everyone with the tools and support we all occasionally need to claim and recover our secure bonds with our precious people.
            </p>
            <p className="text-base text-[#5C6B6B] leading-relaxed mt-5 max-w-2xl">
              We are not therapy. We are not a substitute for clinical care. We are the slow, patient education that comes before, alongside, and after the work of healing — a community that holds the practice between sessions and into a life.
            </p>
            <Link to="/about" className="inline-flex items-center gap-1 text-[#476B6B] font-medium mt-6 text-sm hover:gap-2 transition-all" data-testid="home-learn-more">
              Learn how we got here <ArrowRight size={14} strokeWidth={1.5} />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------- Workshop card on homepage ----------
function WorkshopFeatureCard({ workshop }) {
  return (
    <Link
      to={`/practice/${workshop.slug}`}
      className="card card-hover overflow-hidden block fade-up"
      data-testid={`featured-workshop-${workshop.slug}`}
    >
      <div className="aspect-[4/3] bg-[#E5E1D8] overflow-hidden">
        <img src={workshop.image_url} alt={workshop.title} className="w-full h-full object-cover" />
      </div>
      <div className="p-6">
        <div className="flex items-center gap-3 text-xs text-[#5C6B6B] mb-2">
          <span className="inline-flex items-center gap-1">
            <Calendar size={12} strokeWidth={1.5} />
            {formatDate(workshop.start_date)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Users size={12} strokeWidth={1.5} />
            {workshop.spots_left} spots
          </span>
        </div>
        <h3 className="font-serif text-2xl mb-2">{workshop.title}</h3>
        <p className="text-sm text-[#5C6B6B] line-clamp-2">{workshop.short_description}</p>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm font-medium text-[#476B6B]">${workshop.early_bird_price?.toFixed(0)}+</span>
          <ArrowRight size={16} strokeWidth={1.5} className="text-[#C9A961]" />
        </div>
      </div>
    </Link>
  );
}

// ---------- Featured workshops section ----------
function FeaturedWorkshops({ workshops }) {
  return (
    <section className="container-page py-20">
      <div className="flex items-end justify-between mb-10">
        <div>
          <span className="label">Coming up</span>
          <h2 className="editorial-h2 mt-2">Workshops on the calendar</h2>
        </div>
        <Link to="/practice" className="hidden sm:inline-flex items-center gap-1 text-sm font-medium text-[#476B6B] hover:gap-2 transition-all" data-testid="home-view-all-workshops">
          View all <ArrowRight size={14} strokeWidth={1.5} />
        </Link>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="home-featured-workshops">
        {workshops.map((w) => <WorkshopFeatureCard key={w.id} workshop={w} />)}
      </div>
    </section>
  );
}

// ---------- Single impact card ----------
function ImpactCard({ impact }) {
  return (
    <div className="card p-7" data-testid={`impact-${impact.id}`}>
      <Sparkles size={22} strokeWidth={1.5} className="text-[#C9A961]" />
      <p className="font-serif text-xl mt-3 leading-snug">&ldquo;{impact.what_learned}&rdquo;</p>
      <p className="text-sm text-[#5C6B6B] mt-4 line-clamp-3">{impact.benefits}</p>
      <p className="text-xs text-[#5C6B6B] mt-5 label">— {impact.user_name}</p>
    </div>
  );
}

// ---------- Public impact statements section ----------
function ImpactStatementsSection({ impacts }) {
  if (impacts.length === 0) return null;
  return (
    <section className="bg-white border-y border-[#E5E1D8]">
      <div className="container-page py-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          <div className="lg:col-span-4">
            <span className="label">In their own words</span>
            <h2 className="editorial-h2 mt-2">What past participants say</h2>
            <p className="text-sm text-[#5C6B6B] mt-4 max-w-sm">
              Impact statements written by alumni after they completed our workshops. Shared with permission.
            </p>
          </div>
          <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="home-impact-statements">
            {impacts.map((imp) => <ImpactCard key={imp.id} impact={imp} />)}
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------- How-it-works section ----------
function HowItWorks() {
  return (
    <section className="container-page py-20">
      <span className="label">The three circles</span>
      <h2 className="editorial-h2 mt-2 max-w-xl">A practice that grows with you.</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10" data-testid="how-it-works">
        {HOW_IT_WORKS.map((s) => (
          <div key={s.n} className="card p-8">
            <p className="label text-[#C9A961]">{s.n}</p>
            <h3 className="font-serif text-2xl mt-3">{s.title}</h3>
            <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------- Sponsor campaign teaser ----------
function SponsorCampaignTeaser({ campaign }) {
  if (!campaign) return null;
  return (
    <section className="container-page py-16" data-testid="home-sponsor-campaign-teaser">
      <FeaturedCampaignCard campaign={campaign} testId="home-featured-campaign" />
      <div className="mt-4 text-right">
        <Link to="/campaigns" className="text-xs text-[#476B6B] hover:text-[#0F2424] inline-flex items-center gap-1">
          All campaigns <ArrowRight size={12} strokeWidth={1.5} />
        </Link>
      </div>
    </section>
  );
}

// ---------- Newsletter CTA ----------
function NewsletterCta() {
  return (
    <section className="container-page pb-24">
      <div className="card p-10 lg:p-14 bg-[#476B6B] border-[#476B6B]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div className="text-white">
            <Heart size={28} strokeWidth={1.5} className="text-[#C9A961]" />
            <h2 className="editorial-h2 mt-4 text-white" style={{ color: "white" }}>
              Stay in touch.
            </h2>
            <p className="text-white/80 mt-3 text-sm leading-relaxed max-w-md">
              Occasional notes from the foundation. Workshop announcements, new resources, and a few words from our facilitators.
            </p>
          </div>
          <div>
            <NewsletterSignup />
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------- Founder Collection teaser ----------
function FounderCollectionTeaser({ items }) {
  if (!items || items.length === 0) return null;
  // Prefer the explicitly-flagged homepage feature. Fall back to first item
  // (sorted server-side by created_at) so the teaser always renders.
  const featured = items.find((p) => p.is_homepage_feature) || items[0];
  return (
    <section
      className="border-y border-[#1F3A3A] bg-[#0F2424] text-[#FAF8F5]"
      data-testid="home-founder-teaser"
    >
      <div className="container-page py-14 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 text-[#C9A961]">
              <Sparkles size={14} strokeWidth={1.5} />
              <span className="label !mt-0 text-[#C9A961]">Founder Collection</span>
            </div>
            <h2 className="font-serif text-3xl lg:text-4xl mt-3 leading-tight !text-[#FAF8F5]">
              You are the founder of your own love story.
            </h2>
            <p className="text-base text-[#FAF8F5]/70 mt-4 max-w-xl leading-relaxed">
              A small curated set of quiet objects to carry the practice into the world — and signal
              to your person that you&apos;re choosing to build with them. Five hand-engraved leather
              phrases, plus a few other ways to hold the work close.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                to="/equip#founder-collection"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#C9A961] text-[#0F2424] font-semibold text-sm hover:bg-[#D4B677] transition"
                data-testid="home-founder-shop-cta"
              >
                <ShoppingBag size={14} strokeWidth={1.8} /> Shop the collection
              </Link>
              <Link
                to={`/equip/${featured.id}`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-[#FAF8F5]/30 text-[#FAF8F5] text-sm hover:border-[#C9A961] hover:text-[#C9A961] transition"
                data-testid="home-founder-featured-cta"
              >
                See this patch — ${featured.price?.toFixed(0)} <ArrowRight size={14} strokeWidth={1.5} />
              </Link>
            </div>
          </div>
          <div className="lg:col-span-5">
            <Link
              to={`/equip/${featured.id}`}
              className="block rounded-2xl overflow-hidden bg-[#F4F1EA] shadow-2xl"
              data-testid="home-founder-image-link"
            >
              <img
                src={featured.image_url}
                alt={featured.image_caption || featured.name}
                className="w-full aspect-[4/3] object-cover hover:scale-[1.02] transition-transform duration-500"
              />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------- Page component ----------
export default function Home() {
  const [workshops, setWorkshops] = useState([]);
  const [impacts, setImpacts] = useState([]);
  const [founderItems, setFounderItems] = useState([]);
  const [featuredCampaign, setFeaturedCampaign] = useState(null);

  useEffect(() => {
    api.get("/workshops?status=upcoming").then((r) => setWorkshops(r.data.slice(0, 3))).catch(() => {});
    api.get("/impact-statements?public_only=true").then((r) => setImpacts(r.data.slice(0, 3))).catch(() => {});
    api
      .get("/products?type=merch")
      .then((r) => setFounderItems((r.data || []).filter((p) => p.collection === "founder_collection")))
      .catch(() => {});
    api.get("/campaigns")
      .then((r) => setFeaturedCampaign((r.data?.campaigns || [])[0] || null))
      .catch(() => {});
  }, []);

  return (
    <div data-testid="home-page">
      <Hero />
      <FirstDollarWall />
      <FounderCollectionTeaser items={founderItems} />
      <MissionStrip />
      <FeaturedWorkshops workshops={workshops} />
      <SponsorCampaignTeaser campaign={featuredCampaign} />
      <ImpactStatementsSection impacts={impacts} />
      <HowItWorks />
      <NewsletterCta />
    </div>
  );
}
