import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { Flame } from "lucide-react";

export default function Mission() {
  const [content, setContent] = useState(null);
  useEffect(() => {
    api.get("/foundation/content").then((r) => setContent(r.data)).catch(() => {});
  }, []);
  return (
    <div className="container-page py-24" data-testid="mission-page">
      <div className="max-w-3xl mx-auto text-center">
        <Flame size={32} strokeWidth={1.5} className="text-[#C9A961] mx-auto" />
        <span className="label mt-6 block">Mission statement</span>
        <h1 className="editorial-h1 mt-5">
          <span className="italic">Secure bonds</span><br />
          are our birthright.
        </h1>
        <div className="divider-flame mx-auto" />
        <p className="text-xl text-[#1A2424] leading-relaxed mt-8 font-serif italic">
          {content?.mission_statement}
        </p>
      </div>

      <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto" data-testid="mission-pillars">
        {[
          { id: "empower", title: "Empower everyone", body: "Not the few who can already afford it, not only those already in therapy. Everyone. The tools belong to all of us." },
          { id: "tools", title: "Practical tools", body: "What you can use in the next conversation, with the next person, in the next hour. We don't teach theory for its own sake." },
          { id: "support", title: "Real support", body: "A community that holds you between trainings. Facilitators who answer. Materials that travel with you." },
        ].map((p, i) => (
          <div key={p.id} className="card p-7" data-testid={`mission-pillar-${p.id}`}>
            <span className="label text-[#C9A961]">0{i + 1}</span>
            <h3 className="font-serif text-2xl mt-3">{p.title}</h3>
            <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">{p.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
