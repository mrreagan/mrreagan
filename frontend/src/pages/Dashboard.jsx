import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { Calendar, Sparkles, ArrowRight, X } from "lucide-react";
import { toast } from "sonner";

const formatDate = (iso) => {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

// ---------- Single workshop card ----------
function WorkshopRegistrationCard({ registration, isPast, onCancelled }) {
  const w = registration.workshop;
  const ctaText = isPast
    ? "Leave a review or share impact"
    : registration.checked_in
    ? "Checked in"
    : "Open workshop hub";

  const canCancel = !isPast && !registration.checked_in;

  const cancel = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Cancel your registration for "${w.title}"? Your seat will be offered to the next person on the waitlist.`)) return;
    try {
      const res = await api.delete(`/registrations/${registration.id}`);
      toast.success(res.data?.promoted ? "Seat released. The next waitlister has been notified." : "Registration cancelled.");
      onCancelled(registration.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Cancellation failed");
    }
  };

  return (
    <div
      className="card card-hover overflow-hidden flex relative"
      data-testid={isPast ? `past-reg-${registration.id}` : `reg-${registration.id}`}
    >
      <Link to={`/dashboard/workshops/${w.id}`} className="flex flex-1 min-w-0">
        <div className="w-32 shrink-0 bg-[#E5E1D8]">
          <img src={w.image_url} alt="" className={`w-full h-full object-cover aspect-square ${isPast ? "opacity-80" : ""}`} />
        </div>
        <div className="p-5 flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs text-[#5C6B6B]">
            <Calendar size={12} strokeWidth={1.5} />
            {formatDate(w.start_date)}
          </div>
          <p className="font-serif text-lg mt-1 leading-tight">{w.title}</p>
          <p className={`text-xs mt-2 inline-flex items-center gap-1 ${isPast ? "text-[#476B6B]" : "text-[#5C6B6B]"}`}>
            {ctaText} <ArrowRight size={11} strokeWidth={1.5} />
          </p>
        </div>
      </Link>
      {canCancel && (
        <button
          onClick={cancel}
          className="absolute bottom-3 right-4 text-[11px] text-[#B86A5C] hover:underline inline-flex items-center gap-1"
          data-testid={`cancel-reg-${registration.id}`}
        >
          <X size={11} strokeWidth={1.5} /> Cancel registration
        </button>
      )}
    </div>
  );
}

// ---------- Empty workshops state ----------
function EmptyWorkshops() {
  return (
    <div className="card p-10 text-center" data-testid="dashboard-no-workshops">
      <p className="text-[#5C6B6B]">You haven't registered for any workshops yet.</p>
      <Link to="/practice" className="btn-primary mt-5 inline-flex">
        Find a workshop
      </Link>
    </div>
  );
}

// ---------- Group of workshop cards ----------
function WorkshopsGroup({ label, items, isPast, testId, onCancelled }) {
  return (
    <div>
      <p className="label mb-3">{label}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid={testId}>
        {items.map((r) => (
          <WorkshopRegistrationCard key={r.id} registration={r} isPast={isPast} onCancelled={onCancelled} />
        ))}
      </div>
    </div>
  );
}

// ---------- Workshops section ----------
function WorkshopsSection({ registrations, onCancelled }) {
  const { upcoming, past } = useMemo(() => {
    const now = Date.now();
    return registrations.reduce(
      (acc, r) => {
        if (r.workshop && new Date(r.workshop.start_date).getTime() >= now) acc.upcoming.push(r);
        else if (r.workshop) acc.past.push(r);
        return acc;
      },
      { upcoming: [], past: [] }
    );
  }, [registrations]);

  return (
    <section className="mt-10">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-serif text-2xl">My workshops</h2>
        <Link to="/practice" className="text-sm text-[#476B6B] hover:underline">
          Browse more
        </Link>
      </div>
      {registrations.length === 0 ? (
        <EmptyWorkshops />
      ) : (
        <div className="space-y-6">
          {upcoming.length > 0 && (
            <WorkshopsGroup label="Upcoming" items={upcoming} isPast={false} testId="upcoming-registrations" onCancelled={onCancelled} />
          )}
          {past.length > 0 && (
            <WorkshopsGroup label="Completed" items={past} isPast={true} testId="past-registrations" onCancelled={onCancelled} />
          )}
        </div>
      )}
    </section>
  );
}

// ---------- Journey (impact statements) ----------
function JourneySection({ impactStatements }) {
  if (impactStatements.length === 0) return null;
  return (
    <section className="mt-14" data-testid="dashboard-journey">
      <h2 className="font-serif text-2xl mb-5">My journey</h2>
      <div className="space-y-3">
        {impactStatements.map((imp) => (
          <div key={imp.id} className="card p-6 flex gap-5">
            <Sparkles size={20} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0" />
            <div className="flex-1">
              <p className="font-serif text-lg leading-snug">{imp.what_learned}</p>
              <p className="text-xs text-[#5C6B6B] mt-2">
                {formatDate(imp.created_at)}
                {imp.is_public && " · Shared publicly"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------- Orders section ----------
function OrdersSection({ orders }) {
  return (
    <section className="mt-14">
      <h2 className="font-serif text-2xl mb-5">Order history</h2>
      {orders.length === 0 ? (
        <div className="card p-8 text-center" data-testid="dashboard-no-orders">
          <p className="text-sm text-[#5C6B6B]">No orders yet.</p>
          <Link to="/equip" className="btn-outline mt-4 inline-flex">
            Visit the shop
          </Link>
        </div>
      ) : (
        <div className="space-y-3" data-testid="dashboard-orders">
          {orders.map((o) => (
            <div key={o.id} className="card p-5" data-testid={`order-${o.id}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="label">Order · {formatDate(o.created_at)}</p>
                  <p className="text-sm text-[#1A2424] mt-2">
                    {o.items.length} item{o.items.length !== 1 ? "s" : ""}
                  </p>
                </div>
                <p className="font-serif text-xl">${o.total?.toFixed(2)}</p>
              </div>
              <div className="mt-3 text-xs text-[#5C6B6B]">{o.items.map((i) => i.name).join(" · ")}</div>
              {Array.isArray(o.fulfillments) && o.fulfillments.length > 0 && (
                <div className="mt-3 pt-3 border-t border-dashed border-[#E5E1D8] space-y-1" data-testid={`order-fulfillments-${o.id}`}>
                  {o.fulfillments.map((f, idx) => {
                    const item = o.items[idx];
                    const isPod = !!f.provider;
                    const isIssue = f.status === "failed_to_dispatch";
                    return (
                      <p key={idx} className={`text-[11px] ${isIssue ? "text-[#9E3C3C]" : "text-[#5C6B6B]"}`}>
                        <span className="font-medium text-[#0F2424]">{item?.name || f.product_id?.slice(0, 8)}</span>
                        {" · "}
                        {f.customer_status || f.status}
                        {isPod && f.provider && ` · via ${f.provider}`}
                      </p>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ---------- Main component ----------
export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState({ registrations: [], orders: [], impact_statements: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/dashboard/me")
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="container-page py-20" data-testid="dashboard-loading">
        Loading...
      </div>
    );
  }

  return (
    <div className="container-page py-12" data-testid="dashboard-page">
      <span className="label">Welcome back</span>
      <h1 className="editorial-h1 mt-2" data-testid="dashboard-greeting">
        Hello, {user?.first_name}.
      </h1>
      <div className="divider-flame" />
      <WorkshopsSection
        registrations={data.registrations}
        onCancelled={(regId) =>
          setData((d) => ({ ...d, registrations: d.registrations.filter((r) => r.id !== regId) }))
        }
      />
      <JourneySection impactStatements={data.impact_statements} />
      <OrdersSection orders={data.orders} />
      <section className="mt-14 card p-6 bg-[#FAF8F5] border-[#E5E1D8]" data-testid="dashboard-partner-cta">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <span className="label">Partner network</span>
            <h3 className="font-serif text-xl mt-1">Carry this work forward</h3>
            <p className="text-sm text-[#5C6B6B] max-w-xl mt-1">
              Become a Birthright partner — facilitator, community ally, research collaborator, or vendor.
              Manage applications and your public profile from your partner workspace.
            </p>
          </div>
          <div className="flex gap-2">
            <Link to="/dashboard/partner" className="btn-outline" data-testid="partner-workspace-link">Open workspace</Link>
            <Link to="/partner/apply" className="btn-primary" data-testid="apply-partner-link">Apply</Link>
          </div>
        </div>
      </section>
      <section className="mt-6 card p-6" data-testid="dashboard-bookmarks-cta">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <span className="label">Saved across the site</span>
            <h3 className="font-serif text-xl mt-1">My bookmarks</h3>
            <p className="text-sm text-[#5C6B6B] max-w-xl mt-1">
              Workshops, partners, research, open roles — anything you saved with the bookmark icon lives here.
            </p>
          </div>
          <Link to="/dashboard/bookmarks" className="btn-outline" data-testid="bookmarks-open-link">Open bookmarks</Link>
        </div>
      </section>
    </div>
  );
}
