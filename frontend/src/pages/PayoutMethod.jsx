/* PayoutMethod — where artists / partners set how they receive payouts.
 *
 * URL: /partner/me/payout-method
 *
 * Two options:
 *   1. Stripe Connect — paste your Stripe Connect account ID (acct_…).
 *      Foundation routes patronage + referral payouts via stripe.Transfer.
 *      Simplest for artists who already have a Stripe account; fastest
 *      and lowest-fee disbursement.
 *   2. Manual ACH — bank routing + account number; Foundation initiates
 *      a manual ACH transfer each cycle. Account number is encrypted at
 *      rest; displayed masked.
 *
 * Today's reality: this stores the method on the partner profile so the
 * admin payout flow can use it. True auto-execution via Stripe Connect
 * requires platform-side webhook & transfer wiring (next phase).
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Wallet, ArrowUpRight, Save, ShieldCheck } from "lucide-react";
import api from "../lib/api";

export default function PayoutMethod() {
  const [method, setMethod] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    method_type: "stripe_connect",
    stripe_account_id: "",
    bank_name: "",
    account_holder_name: "",
    routing_number: "",
    account_number: "",
  });

  useEffect(() => {
    api.get("/me/payouts/method").then((r) => {
      const m = r.data || {};
      setMethod(m && m.method_type ? m : null);
      if (m && m.method_type) {
        setForm((f) => ({
          ...f,
          method_type: m.method_type,
          stripe_account_id: m.stripe_account_id || "",
          bank_name: m.bank_name || "",
          account_holder_name: m.account_holder_name || "",
          routing_number: m.routing_number || "",
          // account_number is never returned from the server (encrypted)
        }));
      }
    }).finally(() => setLoading(false));
  }, []);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { method_type: form.method_type };
      if (form.method_type === "stripe_connect") {
        if (!form.stripe_account_id.trim()) {
          toast.error("Enter your Stripe Connect account ID");
          setSaving(false);
          return;
        }
        payload.stripe_account_id = form.stripe_account_id.trim();
      } else {
        if (!form.bank_name || !form.account_holder_name || !form.routing_number || !form.account_number) {
          toast.error("All ACH fields are required");
          setSaving(false);
          return;
        }
        Object.assign(payload, {
          bank_name: form.bank_name,
          account_holder_name: form.account_holder_name,
          routing_number: form.routing_number,
          account_number: form.account_number,
        });
      }
      const r = await api.put("/me/payouts/method", payload);
      setMethod(r.data);
      toast.success("Payout method saved");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="container-page py-12">Loading…</div>;

  return (
    <div className="container-page py-12" data-testid="payout-method-page">
      <span className="label">Partner · payout method</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Wallet size={24} strokeWidth={1.2} /> How you receive payouts
      </h1>
      <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
        Foundation uses this to disburse patronage payouts (your share of
        gallery sales) and inbound referral earnings.
      </p>

      <div className="divider-flame" />

      {method && (
        <section
          className="card p-5 mt-6 max-w-2xl bg-[#FAF8F5]"
          data-testid="payout-method-current"
        >
          <p className="label text-[#476B6B]">Currently on file</p>
          {method.method_type === "stripe_connect" ? (
            <p className="mt-1">
              Stripe Connect · <code className="text-xs bg-white px-2 py-1 border border-[#E5E1D8]">{method.stripe_account_id}</code>
            </p>
          ) : (
            <div className="mt-1 text-sm">
              <p>Manual ACH — {method.bank_name}</p>
              <p className="text-[#5C6B6B]">{method.account_holder_name}</p>
              <p className="text-[#5C6B6B]">Routing: {method.routing_number}</p>
              <p className="text-[#5C6B6B]">Account: ••••{method.account_number_last4 || "****"}</p>
            </div>
          )}
        </section>
      )}

      <section className="card p-6 mt-6 max-w-2xl" data-testid="payout-method-form-section">
        <form onSubmit={save} className="space-y-4">
          <div>
            <label className="label">Method</label>
            <div className="grid grid-cols-2 gap-3 mt-1">
              {[
                { v: "stripe_connect", label: "Stripe Connect", sub: "Recommended" },
                { v: "manual_ach",      label: "Manual ACH",      sub: "U.S. bank" },
              ].map((opt) => (
                <button
                  type="button"
                  key={opt.v}
                  onClick={() => setForm({ ...form, method_type: opt.v })}
                  data-testid={`payout-method-tab-${opt.v}`}
                  className={`p-3 rounded text-left border transition ${
                    form.method_type === opt.v
                      ? "border-[#476B6B] bg-[#F0F6F4]"
                      : "border-[#E5E1D8] hover:border-[#476B6B]"
                  }`}
                >
                  <p className="font-medium text-[#1A2424]">{opt.label}</p>
                  <p className="text-[10px] text-[#5C6B6B] uppercase tracking-wider mt-1">{opt.sub}</p>
                </button>
              ))}
            </div>
          </div>

          {form.method_type === "stripe_connect" ? (
            <div>
              <label className="label">Stripe Connect account ID</label>
              <input
                value={form.stripe_account_id}
                onChange={(e) => setForm({ ...form, stripe_account_id: e.target.value })}
                placeholder="acct_1ABC234DEF5gHIJK"
                className="input-field w-full font-mono text-sm"
                data-testid="payout-stripe-account"
              />
              <p className="text-xs text-[#5C6B6B] mt-2 leading-relaxed">
                Don&apos;t have one yet? Create a free Stripe account at{" "}
                <a href="https://dashboard.stripe.com/register" target="_blank" rel="noreferrer" className="underline text-[#476B6B]">
                  dashboard.stripe.com/register
                </a>{" "}
                — once your account is active, paste your account ID
                (starts with <code className="text-[10px] bg-[#FAF8F5] px-1 py-0.5">acct_</code>) above. Foundation will route your payouts directly through Stripe with no platform fees on your end.
              </p>
            </div>
          ) : (
            <>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="label">Bank name</label>
                  <input
                    value={form.bank_name}
                    onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
                    className="input-field w-full" data-testid="payout-ach-bank"
                  />
                </div>
                <div>
                  <label className="label">Account holder name</label>
                  <input
                    value={form.account_holder_name}
                    onChange={(e) => setForm({ ...form, account_holder_name: e.target.value })}
                    className="input-field w-full" data-testid="payout-ach-holder"
                  />
                </div>
                <div>
                  <label className="label">Routing number</label>
                  <input
                    value={form.routing_number}
                    onChange={(e) => setForm({ ...form, routing_number: e.target.value })}
                    className="input-field w-full font-mono" data-testid="payout-ach-routing"
                  />
                </div>
                <div>
                  <label className="label">Account number</label>
                  <input
                    type="password"
                    value={form.account_number}
                    onChange={(e) => setForm({ ...form, account_number: e.target.value })}
                    className="input-field w-full font-mono" data-testid="payout-ach-account"
                    placeholder={method?.method_type === "manual_ach" ? "leave blank to keep current" : ""}
                  />
                </div>
              </div>
              <p className="text-xs text-[#5C6B6B] flex items-start gap-2 mt-2">
                <ShieldCheck size={14} strokeWidth={1.6} className="text-[#476B6B] shrink-0 mt-0.5" />
                Account number is encrypted at rest. Only the last 4
                digits are ever displayed back to you or anyone else.
              </p>
            </>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={saving}
              className="btn-primary inline-flex items-center gap-2"
              data-testid="payout-method-save"
            >
              <Save size={14} strokeWidth={1.6} />
              {saving ? "Saving…" : "Save payout method"}
            </button>
          </div>
        </form>
      </section>

      <div className="mt-8 max-w-2xl">
        <Link
          to="/partner/me/off-site-report"
          className="text-xs uppercase tracking-[0.18em] text-[#476B6B] hover:text-[#1A2424] inline-flex items-center gap-1"
        >
          Submit a quarterly off-site report <ArrowUpRight size={12} strokeWidth={1.6} />
        </Link>
      </div>
    </div>
  );
}
