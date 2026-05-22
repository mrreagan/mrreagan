import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { Calendar, ShoppingBag, Sparkles, ArrowRight } from "lucide-react";

const formatDate = (iso) => {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState({ registrations: [], orders: [], impact_statements: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/dashboard/me").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="container-page py-20" data-testid="dashboard-loading">Loading...</div>;

  const upcoming = data.registrations.filter(
    (r) => r.workshop && new Date(r.workshop.start_date) >= new Date()
  );
  const past = data.registrations.filter(
    (r) => r.workshop && new Date(r.workshop.start_date) < new Date()
  );

  return (
    <div className="container-page py-12" data-testid="dashboard-page">
      <span className="label">Welcome back</span>
      <h1 className="editorial-h1 mt-2" data-testid="dashboard-greeting">Hello, {user?.first_name}.</h1>
      <div className="divider-flame" />

      {/* My Workshops */}
      <section className="mt-10">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-serif text-2xl">My workshops</h2>
          <Link to="/workshops" className="text-sm text-[#476B6B] hover:underline">Browse more</Link>
        </div>
        {data.registrations.length === 0 ? (
          <div className="card p-10 text-center" data-testid="dashboard-no-workshops">
            <p className="text-[#5C6B6B]">You haven't registered for any workshops yet.</p>
            <Link to="/workshops" className="btn-primary mt-5 inline-flex">Find a workshop</Link>
          </div>
        ) : (
          <div className="space-y-6">
            {upcoming.length > 0 && (
              <div>
                <p className="label mb-3">Upcoming</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="upcoming-registrations">
                  {upcoming.map((r) => (
                    <Link key={r.id} to={`/dashboard/workshops/${r.workshop.id}`} className="card card-hover overflow-hidden flex" data-testid={`reg-${r.id}`}>
                      <div className="w-32 shrink-0 bg-[#E5E1D8]">
                        <img src={r.workshop.image_url} alt="" className="w-full h-full object-cover aspect-square" />
                      </div>
                      <div className="p-5 flex-1">
                        <div className="flex items-center gap-2 text-xs text-[#5C6B6B]">
                          <Calendar size={12} strokeWidth={1.5} />
                          {formatDate(r.workshop.start_date)}
                        </div>
                        <p className="font-serif text-lg mt-1 leading-tight">{r.workshop.title}</p>
                        <p className="text-xs text-[#5C6B6B] mt-2 inline-flex items-center gap-1">
                          {r.checked_in ? "Checked in" : "Open workshop hub"} <ArrowRight size={11} strokeWidth={1.5} />
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {past.length > 0 && (
              <div>
                <p className="label mb-3">Completed</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {past.map((r) => (
                    <Link key={r.id} to={`/dashboard/workshops/${r.workshop.id}`} className="card card-hover overflow-hidden flex" data-testid={`past-reg-${r.id}`}>
                      <div className="w-32 shrink-0 bg-[#E5E1D8]">
                        <img src={r.workshop.image_url} alt="" className="w-full h-full object-cover aspect-square opacity-80" />
                      </div>
                      <div className="p-5 flex-1">
                        <div className="flex items-center gap-2 text-xs text-[#5C6B6B]">
                          <Calendar size={12} strokeWidth={1.5} />
                          {formatDate(r.workshop.start_date)}
                        </div>
                        <p className="font-serif text-lg mt-1 leading-tight">{r.workshop.title}</p>
                        <p className="text-xs text-[#476B6B] mt-2 inline-flex items-center gap-1">
                          Leave a review or share impact <ArrowRight size={11} strokeWidth={1.5} />
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* My Journey */}
      {data.impact_statements.length > 0 && (
        <section className="mt-14" data-testid="dashboard-journey">
          <h2 className="font-serif text-2xl mb-5">My journey</h2>
          <div className="space-y-3">
            {data.impact_statements.map((imp) => (
              <div key={imp.id} className="card p-6 flex gap-5">
                <Sparkles size={20} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0" />
                <div className="flex-1">
                  <p className="font-serif text-lg leading-snug">{imp.what_learned}</p>
                  <p className="text-xs text-[#5C6B6B] mt-2">{formatDate(imp.created_at)}{imp.is_public && " · Shared publicly"}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Orders */}
      <section className="mt-14">
        <h2 className="font-serif text-2xl mb-5">Order history</h2>
        {data.orders.length === 0 ? (
          <div className="card p-8 text-center" data-testid="dashboard-no-orders">
            <p className="text-sm text-[#5C6B6B]">No orders yet.</p>
            <Link to="/shop" className="btn-outline mt-4 inline-flex">Visit the shop</Link>
          </div>
        ) : (
          <div className="space-y-3" data-testid="dashboard-orders">
            {data.orders.map((o) => (
              <div key={o.id} className="card p-5" data-testid={`order-${o.id}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="label">Order · {formatDate(o.created_at)}</p>
                    <p className="text-sm text-[#1A2424] mt-2">{o.items.length} item{o.items.length !== 1 ? "s" : ""}</p>
                  </div>
                  <p className="font-serif text-xl">${o.total?.toFixed(2)}</p>
                </div>
                <div className="mt-3 text-xs text-[#5C6B6B]">
                  {o.items.map((i) => i.name).join(" · ")}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
