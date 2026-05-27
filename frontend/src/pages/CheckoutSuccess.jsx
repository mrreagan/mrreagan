import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useCart } from "../contexts/CartContext";
import { CheckCircle2, AlertCircle } from "lucide-react";

const SUCCESS_MESSAGES = {
  workshop: "You're registered. A confirmation is on its way.",
  order: "Your order is confirmed. We'll be in touch with shipping details.",
  donation: "Your gift sustains the foundation's work. We're grateful.",
  sponsorship: "Welcome, sponsor. We'll be in touch shortly with next steps.",
};

const MAX_POLL_ATTEMPTS = 10;
const POLL_INTERVAL_MS = 2000;

function LoadingState() {
  return (
    <>
      <div className="w-16 h-16 mx-auto rounded-full border-2 border-[#C9A961] border-t-transparent animate-spin" />
      <h1 className="font-serif text-3xl mt-6">Confirming your payment</h1>
      <p className="text-sm text-[#5C6B6B] mt-3">A moment please…</p>
    </>
  );
}

function PaidState({ type }) {
  return (
    <>
      <CheckCircle2 size={56} strokeWidth={1.5} className="text-[#2E5C46] mx-auto" data-testid="success-icon" />
      <h1 className="editorial-h1 mt-6">Thank you.</h1>
      <p className="text-base text-[#5C6B6B] mt-4">
        {SUCCESS_MESSAGES[type] || "Your payment is complete."}
      </p>
      <div className="mt-8 flex gap-3 justify-center">
        {type === "workshop" ? (
          <Link to="/dashboard" className="btn-primary" data-testid="success-dashboard-btn">
            Go to my dashboard
          </Link>
        ) : (
          <Link to="/" className="btn-primary">
            Return home
          </Link>
        )}
        <Link to="/practice" className="btn-outline">
          Explore more
        </Link>
      </div>
    </>
  );
}

function FailedState() {
  return (
    <>
      <AlertCircle size={56} strokeWidth={1.5} className="text-[#9E3C3C] mx-auto" />
      <h1 className="editorial-h1 mt-6">Payment didn't complete.</h1>
      <p className="text-base text-[#5C6B6B] mt-4">No charge was made. You can try again whenever you're ready.</p>
      <Link to="/" className="btn-primary mt-8 inline-flex">
        Return home
      </Link>
    </>
  );
}

function PendingState() {
  return (
    <>
      <AlertCircle size={48} strokeWidth={1.5} className="text-[#C9A961] mx-auto" />
      <h1 className="font-serif text-3xl mt-6">Still processing</h1>
      <p className="text-sm text-[#5C6B6B] mt-4">
        Your payment may still be processing. Check your email for confirmation, or your dashboard in a few minutes.
      </p>
      <Link to="/dashboard" className="btn-primary mt-6 inline-flex">
        Go to dashboard
      </Link>
    </>
  );
}

function classifyStatus(status) {
  if (status.checking) return "checking";
  if (status.payment_status === "paid") return "paid";
  if (status.status === "expired" || status.payment_status === "unpaid") return "failed";
  return "pending";
}

export default function CheckoutSuccess() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const type = params.get("type");
  const [status, setStatus] = useState({ payment_status: "pending", checking: true });
  const [attempts, setAttempts] = useState(0);
  const { clear } = useCart();

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await api.get(`/checkout/status/${sessionId}`);
      setStatus({ ...data, checking: false });
      if (data.payment_status === "paid" && type === "order") clear();
      return data;
    } catch {
      setStatus({ payment_status: "unknown", checking: false });
      return null;
    }
  }, [sessionId, type, clear]);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      const data = await fetchStatus();
      if (cancelled || !data) return;
      if (data.payment_status === "paid" || data.status === "expired") return;
      if (attempts < MAX_POLL_ATTEMPTS) {
        setTimeout(() => {
          if (!cancelled) setAttempts((a) => a + 1);
        }, POLL_INTERVAL_MS);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, attempts, fetchStatus]);

  const view = classifyStatus(status);

  return (
    <div className="container-page py-24 max-w-xl mx-auto text-center" data-testid="checkout-success-page">
      {view === "checking" && <LoadingState />}
      {view === "paid" && <PaidState type={type} />}
      {view === "failed" && <FailedState />}
      {view === "pending" && <PendingState />}
    </div>
  );
}
