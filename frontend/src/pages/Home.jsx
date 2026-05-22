import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { ArrowRight, Calendar, Users, Star, Flame, Sparkles, Heart } from "lucide-react";
import { NewsletterSignup } from "../components/Newsletter";

const HERO_BG = "https://static.prod-images.emergentagent.com/jobs/c61b4345-eef4-4783-a5af-85e8af10eaf3/images/10154eafef8a2623b8b4e86a0d0a8065334110989eba28a8c99077e78f19d1fa.png";
const COMMUNITY_IMG_1 = "https://images.unsplash.com/photo-1634155938686-24a26c55d71a?w=1200";
const COMMUNITY_IMG_2 = "https://images.unsplash.com/photo-1655337690436-98778f38d613?w=900";

const formatDate = (iso) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
};

export default function Home() {
  const [workshops, setWorkshops] = useState([]);
  const [impacts, setImpacts] = useState([]);

  useEffect(() => {
    api.get("/workshops?status=upcoming").then((r) => setWorkshops(r.data.slice(0, 3))).catch(() => {});
    api.get("/impact-statements?public_only=true").then((r) => setImpacts(r.data.slice(0, 3))).catch(() => {});
  }, []);

  return (
    <div data-testid="home-page">
      {/* HERO */}
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
                <Link to="/workshops" className="btn-primary" data-testid="hero-browse-workshops">
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

      {/* MISSION STRIP */}
      <section className="border-y border-[#E5E1D8] bg-white">
        <div className="container-page py-14 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
            <div className="lg:col-span-4">
              <span className="label">Our mission</span>
              <p className="editorial-h2 mt-3">
                We are<br />the practice ground.
              </p>
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

      {/* FEATURED WORKSHOPS */}
      <section className="container-page py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <span className="label">Coming up</span>
            <h2 className="editorial-h2 mt-2">Workshops on the calendar</h2>
          </div>
          <Link to="/workshops" className="hidden sm:inline-flex items-center gap-1 text-sm font-medium text-[#476B6B] hover:gap-2 transition-all" data-testid="home-view-all-workshops">
            View all <ArrowRight size={14} strokeWidth={1.5} />
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="home-featured-workshops">
          {workshops.map((w) => (
            <Link
              key={w.id}
              to={`/workshops/${w.slug}`}
              className="card card-hover overflow-hidden block fade-up"
              data-testid={`featured-workshop-${w.slug}`}
            >
              <div className="aspect-[4/3] bg-[#E5E1D8] overflow-hidden">
                <img src={w.image_url} alt={w.title} className="w-full h-full object-cover" />
              </div>
              <div className="p-6">
                <div className="flex items-center gap-3 text-xs text-[#5C6B6B] mb-2">
                  <span className="inline-flex items-center gap-1"><Calendar size={12} strokeWidth={1.5} />{formatDate(w.start_date)}</span>
                  <span className="inline-flex items-center gap-1"><Users size={12} strokeWidth={1.5} />{w.spots_left} spots</span>
                </div>
                <h3 className="font-serif text-2xl mb-2">{w.title}</h3>
                <p className="text-sm text-[#5C6B6B] line-clamp-2">{w.short_description}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-sm font-medium text-[#476B6B]">${w.early_bird_price?.toFixed(0)}+</span>
                  <ArrowRight size={16} strokeWidth={1.5} className="text-[#C9A961]" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* IMPACT STATEMENTS */}
      {impacts.length > 0 && (
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
                {impacts.map((imp) => (
                  <div key={imp.id} className="card p-7" data-testid={`impact-${imp.id}`}>
                    <Sparkles size={22} strokeWidth={1.5} className="text-[#C9A961]" />
                    <p className="font-serif text-xl mt-3 leading-snug">"{imp.what_learned}"</p>
                    <p className="text-sm text-[#5C6B6B] mt-4 line-clamp-3">{imp.benefits}</p>
                    <p className="text-xs text-[#5C6B6B] mt-5 label">— {imp.user_name}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* HOW IT WORKS */}
      <section className="container-page py-20">
        <span className="label">The three circles</span>
        <h2 className="editorial-h2 mt-2 max-w-xl">A practice that grows with you.</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10" data-testid="how-it-works">
          {[
            { n: "01", title: "Foundations", body: "Begin here. Learn the language and felt-sense of secure bonds in a weekend immersion." },
            { n: "02", title: "Practice", body: "Live skills work with certified facilitators. Smaller cohorts. Deeper application." },
            { n: "03", title: "Living the Work", body: "An ongoing peer community. Monthly circles. The practice in real life." },
          ].map((s) => (
            <div key={s.n} className="card p-8">
              <p className="label text-[#C9A961]">{s.n}</p>
              <h3 className="font-serif text-2xl mt-3">{s.title}</h3>
              <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* NEWSLETTER */}
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
    </div>
  );
}
