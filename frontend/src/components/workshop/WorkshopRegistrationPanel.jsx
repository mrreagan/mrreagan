import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../../lib/api";
import downloadIcs from "../../lib/calendar";
import { formatDate } from "./WorkshopSections";

/**
 * Sidebar card with pricing, register/waitlist button, and post-registration actions.
 */
export default function WorkshopRegistrationPanel({ workshop, registered, slug, user }) {
  const navigate = useNavigate();
  const [registering, setRegistering] = useState(false);
  const [waitlisted, setWaitlisted] = useState(false);

  const isEarlyBird = workshop.early_bird_until && new Date(workshop.early_bird_until) > new Date();
  const currentPrice = isEarlyBird ? workshop.early_bird_price : workshop.regular_price;
  const isFull = workshop.spots_left <= 0;
  const isPast = workshop.status === "completed";

  const handleRegister = async () => {
    if (!user) {
      toast.info("Please sign in to register");
      navigate("/login", { state: { from: `/workshops/${slug}` } });
      return;
    }
    setRegistering(true);
    try {
      const { data } = await api.post("/checkout/workshop", {
        workshop_id: workshop.id,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setRegistering(false);
    }
  };

  const handleJoinWaitlist = async () => {
    if (!user) {
      navigate("/login", { state: { from: `/workshops/${slug}` } });
      return;
    }
    try {
      const { data } = await api.post(`/workshops/${workshop.id}/waitlist`, {});
      setWaitlisted(true);
      toast.success(data.message);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not join waitlist");
    }
  };

  return (
    <div className="lg:col-span-5">
      <div className="card overflow-hidden sticky top-24" data-testid="workshop-register-card">
        <div className="aspect-[4/3]">
          <img src={workshop.image_url} alt={workshop.title} className="w-full h-full object-cover" />
        </div>
        <div className="p-6">
          {isPast ? (
            <PastWorkshopCta />
          ) : (
            <ActiveWorkshopCta
              workshop={workshop}
              isEarlyBird={isEarlyBird}
              currentPrice={currentPrice}
              isFull={isFull}
              registered={registered}
              registering={registering}
              waitlisted={waitlisted}
              onRegister={handleRegister}
              onJoinWaitlist={handleJoinWaitlist}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function PastWorkshopCta() {
  return (
    <>
      <span className="label">This workshop has ended</span>
      <p className="text-sm text-[#5C6B6B] mt-2">Read past participant impact below or browse upcoming.</p>
      <Link to="/workshops" className="btn-primary w-full justify-center mt-5">
        Browse upcoming
      </Link>
    </>
  );
}

function ActiveWorkshopCta({
  workshop, isEarlyBird, currentPrice, isFull, registered, registering, waitlisted, onRegister, onJoinWaitlist,
}) {
  return (
    <>
      {isEarlyBird && (
        <div className="mb-3">
          <span className="label text-[#C9A961]">Early-bird pricing</span>
          <p className="text-xs text-[#5C6B6B] mt-1">Ends {formatDate(workshop.early_bird_until)}</p>
        </div>
      )}
      <div className="flex items-baseline gap-3">
        <span className="font-serif text-4xl text-[#1A2424]" data-testid="workshop-price">
          ${currentPrice?.toFixed(0)}
        </span>
        {isEarlyBird && <span className="text-base text-[#5C6B6B] line-through">${workshop.regular_price?.toFixed(0)}</span>}
      </div>
      <PrimaryAction
        workshop={workshop}
        registered={registered}
        isFull={isFull}
        registering={registering}
        waitlisted={waitlisted}
        onRegister={onRegister}
        onJoinWaitlist={onJoinWaitlist}
      />
      {registered && (
        <button
          onClick={() => downloadIcs(workshop)}
          className="btn-outline w-full justify-center mt-3 text-sm"
          data-testid="workshop-add-calendar"
        >
          Add to Calendar
        </button>
      )}
    </>
  );
}

function PrimaryAction({ workshop, registered, isFull, registering, waitlisted, onRegister, onJoinWaitlist }) {
  if (registered) {
    return (
      <Link
        to={`/dashboard/workshops/${workshop.id}`}
        className="btn-primary w-full justify-center mt-5"
        data-testid="workshop-go-to-hub"
      >
        Go to workshop hub
      </Link>
    );
  }
  if (isFull) {
    return (
      <button onClick={onJoinWaitlist} disabled={waitlisted} className="btn-outline w-full justify-center mt-5" data-testid="workshop-waitlist">
        {waitlisted ? "On the waitlist" : "Join the waitlist"}
      </button>
    );
  }
  return (
    <button
      onClick={onRegister}
      disabled={registering}
      className="btn-primary w-full justify-center mt-5"
      data-testid="workshop-register-btn"
    >
      {registering ? "Loading..." : "Register"}
    </button>
  );
}
