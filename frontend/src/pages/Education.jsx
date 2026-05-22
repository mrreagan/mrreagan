import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { BookOpen, Users, Infinity as InfinityIcon, ArrowRight } from "lucide-react";

export default function Education() {
  const [content, setContent] = useState(null);
  useEffect(() => {
    api.get("/foundation/content").then((r) => setContent(r.data)).catch(() => {});
  }, []);
  return (
    <div className="container-page py-20" data-testid="education-page">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-5">
          <span className="label">Educational structure</span>
          <h1 className="editorial-h1 mt-3">A practice, not a curriculum.</h1>
          <div className="divider-flame" />
          <p className="text-base text-[#1A2424] leading-relaxed">
            {content?.education_structure}
          </p>
        </div>
        <div className="lg:col-span-6 lg:col-start-7 space-y-4" data-testid="education-circles">
          {[
            { icon: BookOpen, title: "Foundations", subtitle: "Two-day weekend immersions", body: "Open to anyone. No prerequisites. Designed as the on-ramp to a lifetime of relational practice.", num: "01" },
            { icon: Users, title: "Practice", subtitle: "Small cohort skill labs", body: "For those continuing the work. Pair-practice, supervised reps, and targeted exercises with certified facilitators.", num: "02" },
            { icon: InfinityIcon, title: "Living the Work", subtitle: "Monthly community circles", body: "An ongoing peer container for alumni. Keep the practice alive between formal trainings. Optional, ongoing.", num: "03" },
          ].map((c) => (
            <div key={c.title} className="card p-7 flex gap-5">
              <div className="shrink-0 w-12 h-12 rounded-full border border-[#E5E1D8] flex items-center justify-center text-[#C9A961]">
                <c.icon size={20} strokeWidth={1.5} />
              </div>
              <div className="flex-1">
                <div className="flex items-baseline justify-between">
                  <span className="label">{c.num}</span>
                  <span className="text-xs text-[#5C6B6B]">{c.subtitle}</span>
                </div>
                <h3 className="font-serif text-2xl mt-1">{c.title}</h3>
                <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{c.body}</p>
              </div>
            </div>
          ))}
          <div className="pt-4">
            <Link to="/workshops" className="btn-primary" data-testid="education-cta">
              Browse upcoming workshops <ArrowRight size={16} strokeWidth={1.5} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
