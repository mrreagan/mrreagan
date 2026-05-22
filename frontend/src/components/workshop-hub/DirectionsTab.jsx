import React, { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";

function LocationCard({ reg }) {
  return (
    <div className="lg:col-span-2 card p-7">
      <span className="label">Where to go</span>
      <h3 className="font-serif text-2xl mt-2">{reg.location_name}</h3>
      <p className="text-sm text-[#5C6B6B] mt-1">{reg.location_address}</p>
      {reg.map_url && (
        <a href={reg.map_url} target="_blank" rel="noreferrer" className="btn-outline mt-4 inline-flex text-sm">
          Open in maps
        </a>
      )}
      {reg.directions_notes && (
        <>
          <span className="label mt-7 block">Notes from the facilitator</span>
          <p className="text-sm text-[#1A2424] mt-3 leading-relaxed whitespace-pre-line">{reg.directions_notes}</p>
        </>
      )}
    </div>
  );
}

function CheckedInPanel() {
  return (
    <>
      <CheckCircle2 size={48} strokeWidth={1.5} className="text-[#2E5C46]" />
      <h3 className="font-serif text-2xl mt-4">You're checked in.</h3>
      <p className="text-sm text-[#5C6B6B] mt-2">Welcome. Find a seat and breathe.</p>
    </>
  );
}

function CheckInForm({ qrUrl, code, setCode, onSubmit, loading }) {
  return (
    <>
      <span className="label">Check-in</span>
      <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">
        Once you arrive, your facilitator will share a check-in code. Or show them this QR code.
      </p>
      <div className="my-5 flex justify-center">
        <img src={qrUrl} alt="Check-in QR" className="rounded-lg border border-[#E5E1D8]" data-testid="check-in-qr" />
      </div>
      <form onSubmit={onSubmit} className="space-y-3">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Enter check-in code"
          className="input-field text-center uppercase tracking-widest"
          data-testid="check-in-code-input"
        />
        <button type="submit" disabled={loading || !code} className="btn-primary w-full justify-center" data-testid="check-in-submit">
          {loading ? "..." : "Check in"}
        </button>
      </form>
    </>
  );
}

export default function DirectionsTab({ workshop, reg }) {
  const [code, setCode] = useState("");
  const [checkedIn, setCheckedIn] = useState(reg.registration?.checked_in || false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post(`/workshops/${workshop.id}/check-in`, { code });
      setCheckedIn(true);
      toast.success("You're checked in.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Invalid code");
    } finally {
      setLoading(false);
    }
  };

  const qrText = `BIRTHRIGHT|${workshop.id}|${reg.registration?.id}`;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(qrText)}`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="tab-directions">
      <LocationCard reg={reg} />
      <div className="card p-7" data-testid="check-in-card">
        {checkedIn ? (
          <CheckedInPanel />
        ) : (
          <CheckInForm qrUrl={qrUrl} code={code} setCode={setCode} onSubmit={submit} loading={loading} />
        )}
      </div>
    </div>
  );
}
