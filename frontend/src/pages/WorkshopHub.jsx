import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  MapPin,
  MessageCircle,
  MessageSquare,
  HelpCircle,
  ShoppingBag,
  Star,
  Sparkles,
  LifeBuoy,
  Camera,
} from "lucide-react";
import DirectionsTab from "../components/workshop-hub/DirectionsTab";
import DiscussionTab from "../components/workshop-hub/DiscussionTab";
import ChatTab from "../components/workshop-hub/ChatTab";
import MaterialsTab from "../components/workshop-hub/MaterialsTab";
import ReviewTab from "../components/workshop-hub/ReviewTab";
import ImpactTab from "../components/workshop-hub/ImpactTab";
import SupportTab from "../components/workshop-hub/SupportTab";
import PhotosTab from "../components/workshop-hub/PhotosTab";

const TABS = [
  { id: "directions", label: "Directions & Check-in", icon: MapPin },
  { id: "discussion", label: "Discussion", icon: MessageSquare },
  { id: "qa", label: "Q&A", icon: HelpCircle },
  { id: "chat", label: "Chat", icon: MessageCircle },
  { id: "materials", label: "Materials", icon: ShoppingBag },
  { id: "photos", label: "Photos", icon: Camera },
  { id: "review", label: "Review", icon: Star },
  { id: "impact", label: "Impact", icon: Sparkles },
  { id: "support", label: "Support", icon: LifeBuoy },
];

function TabBar({ active, onChange }) {
  return (
    <div className="mt-8 border-b border-[#E5E1D8] overflow-x-auto no-scrollbar" data-testid="hub-tabs">
      <div className="flex gap-1 min-w-max">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={`px-4 py-3 text-sm font-medium flex items-center gap-2 border-b-2 transition ${
              active === t.id ? "border-[#476B6B] text-[#476B6B]" : "border-transparent text-[#5C6B6B] hover:text-[#1A2424]"
            }`}
            data-testid={`hub-tab-${t.id}`}
          >
            <t.icon size={15} strokeWidth={1.5} /> {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function TabContent({ tab, workshop, reg, user }) {
  switch (tab) {
    case "directions":
      return <DirectionsTab workshop={workshop} reg={reg} />;
    case "discussion":
      return <DiscussionTab workshop={workshop} type="discussion" />;
    case "qa":
      return <DiscussionTab workshop={workshop} type="qa" />;
    case "chat":
      return <ChatTab workshop={workshop} user={user} />;
    case "materials":
      return <MaterialsTab workshop={workshop} />;
    case "photos":
      return <PhotosTab workshop={workshop} user={user} />;
    case "review":
      return <ReviewTab workshop={workshop} />;
    case "impact":
      return <ImpactTab workshop={workshop} />;
    case "support":
      return <SupportTab workshop={workshop} />;
    default:
      return null;
  }
}

export default function WorkshopHub() {
  const { id } = useParams();
  const { user } = useAuth();
  const [workshop, setWorkshop] = useState(null);
  const [reg, setReg] = useState(null);
  const [tab, setTab] = useState("directions");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [wRes, rRes] = await Promise.all([
          api.get(`/workshops/${id}`),
          api.get(`/workshops/${id}/my-registration`),
        ]);
        if (cancelled) return;
        setWorkshop(wRes.data);
        setReg(rRes.data);
      } catch (err) {
        console.error("Workshop hub load failed:", err?.message || err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!workshop || !reg) {
    return <div className="container-page py-20" data-testid="hub-loading">Loading...</div>;
  }
  if (!reg.registered) {
    return (
      <div className="container-page py-20 text-center">
        <p>You're not registered for this workshop.</p>
        <Link to="/workshops" className="btn-primary mt-4 inline-flex">Browse workshops</Link>
      </div>
    );
  }

  return (
    <div className="container-page py-12" data-testid="workshop-hub-page">
      <Link to="/dashboard" className="text-sm text-[#5C6B6B] hover:text-[#476B6B]">← Dashboard</Link>
      <span className="label mt-4 block">Workshop hub</span>
      <h1 className="editorial-h1 mt-2" data-testid="hub-title">{workshop.title}</h1>
      <p className="text-sm text-[#5C6B6B] mt-3">
        With {workshop.facilitator?.first_name} {workshop.facilitator?.last_name} ·{" "}
        {new Date(workshop.start_date).toLocaleDateString("en-US", { dateStyle: "long" })}
      </p>

      <TabBar active={tab} onChange={setTab} />
      <div className="mt-8">
        <TabContent tab={tab} workshop={workshop} reg={reg} user={user} />
      </div>
    </div>
  );
}
