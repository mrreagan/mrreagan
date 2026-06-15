import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Wallet, FileText, CreditCard, CheckCircle2 } from "lucide-react";

const CLASSIFICATIONS = [
  { v: "individual", l: "Individual / sole-proprietor" },
  { v: "sole_proprietor", l: "Single-member LLC (treated as disregarded entity)" },
  { v: "c_corporation", l: "C Corporation" },
  { v: "s_corporation", l: "S Corporation" },
  { v: "partnership", l: "Partnership" },
  { v: "trust_estate", l: "Trust / estate" },
  { v: "llc", l: "Limited liability company" },
];

const EMPTY_W9 = {
  full_name: "", business_name: "", classification: "individual",
  exempt_payee_code: "", address_line1: "", address_line2: "",
  city: "", state: "", zip_code: "", country: "US",
  tin: "", tin_type: "SSN", signature_name: "",
};

const EMPTY_METHOD = {
  method_type: "stripe_connect", stripe_account_id: "",
  bank_name: "", account_holder_name: "", routing_number: "", account_number: "",
};

export default function PartnerPayouts() {
  const [tab, setTab] = useState("ledger");
  const [ledger, setLedger] = useState(null);
  const [w9, setW9] = useState(null);
  const [method, setMethod] = useState(null);
  const [w9Form, setW9Form] = useState(EMPTY_W9);
  const [methodForm, setMethodForm] = useState(EMPTY_METHOD);

  const load = () => {
    Promise.all([
      api.get("/me/payouts").then((r) => setLedger(r.data)),
      api.get("/me/payouts/w9").then((r) => { setW9(r.data); if (r.data) setW9Form({ ...EMPTY_W9, ...r.data, tin: "" }); }),
      api.get("/me/payouts/method").then((r) => { setMethod(r.data); if (r.data) setMethodForm({ ...EMPTY_METHOD, ...r.data, account_number: "" }); }),
    ]);
  };
  useEffect(load, []);

  return (
    <div className="container-page py-12" data-testid="partner-payouts-page">
      <span className="label">Partner</span>
      <h1 className="editorial-h1 mt-2">Payouts</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Your combined earnings from on-site referrals and off-site sales credits. Submit your W9 and payout method to be eligible for disbursement.
      </p>

      <div className="flex gap-2 mt-6" data-testid="payouts-tabs">
        {[{ k: "ledger", l: "Ledger", Icon: Wallet }, { k: "w9", l: "W9 form", Icon: FileText }, { k: "method", l: "Payout method", Icon: CreditCard }].map(({ k, l, Icon }) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              tab === k ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`tab-${k}`}
          >
            <Icon size={11} strokeWidth={1.5} /> {l}
          </button>
        ))}
      </div>

      {tab === "ledger" && <Ledger ledger={ledger} />}
      {tab === "w9" && <W9Tab w9={w9} form={w9Form} setForm={setW9Form} onSaved={load} />}
      {tab === "method" && <MethodTab method={method} form={methodForm} setForm={setMethodForm} onSaved={load} />}
    </div>
  );
}

function Ledger({ ledger }) {
  if (!ledger) return <p className="text-sm text-[#5C6B6B] mt-6">Loading...</p>;
  const isReady = ledger.ready_for_payout;
  return (
    <div className="mt-6 space-y-4" data-testid="ledger-tab">
      {(ledger.next_disbursement_date || !isReady) && (
        <div
          className={`card p-4 ${isReady ? "border-[#2E5C46] bg-[#F4F8F4]" : "border-[#C9A961] bg-[#FFFBEF]"}`}
          data-testid="next-disbursement-card"
        >
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                {ledger.cadence ? `Disbursements run ${ledger.cadence}` : "Disbursements"}
              </p>
              {ledger.next_disbursement_date ? (
                <p className="font-serif text-lg" data-testid="next-disbursement-date">
                  Next run: {new Date(ledger.next_disbursement_date).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
                </p>
              ) : (
                <p className="font-serif text-lg">Next run not yet scheduled</p>
              )}
            </div>
            {!isReady && (
              <p className="text-xs text-[#8B7128] max-w-xs" data-testid="payout-not-ready">
                You&apos;re not yet ready for payout. {!ledger.w9_on_file && "W9 needed. "}{!ledger.method_on_file && "Payout method needed."}
              </p>
            )}
            {isReady && (
              <p className="text-xs text-[#2E5C46] inline-flex items-center gap-1" data-testid="payout-ready">
                <CheckCircle2 size={12} strokeWidth={1.5} /> Ready for disbursement
              </p>
            )}
          </div>
        </div>
      )}
      <div className="grid sm:grid-cols-3 gap-3">
        <Stat label="Earned, unpaid" value={`$${ledger.totals.earned_unpaid.toFixed(2)}`} testid="totals-earned" />
        <Stat label="Paid lifetime" value={`$${ledger.totals.paid_lifetime.toFixed(2)}`} testid="totals-paid" />
        <Stat label="All-time" value={`$${ledger.totals.all_time.toFixed(2)}`} testid="totals-all" />
      </div>
      <div className="space-y-2">
        {ledger.entries.length === 0 && (
          <div className="card p-8 text-center text-sm text-[#5C6B6B]">No earnings yet.</div>
        )}
        {ledger.entries.map((e) => (
          <div key={`${e.source}-${e.id}`} className="card p-4 flex items-start justify-between gap-3" data-testid={`ledger-entry-${e.id}`}>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">${e.amount_usd.toFixed(2)}{e.rev_share_pct ? ` · ${e.rev_share_pct}%` : ""}</p>
              <p className="text-xs text-[#5C6B6B]">
                {e.source === "on_site_referral" ? "On-site referral" : "Off-site sales credit"} · earned {new Date(e.earned_at).toLocaleDateString()}
                {e.paid_at && ` · paid ${new Date(e.paid_at).toLocaleDateString()}`}
              </p>
              {e.status === "paid" && (e.payout_method || e.payout_reference) && (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wider" data-testid={`paid-detail-${e.id}`}>
                  {e.payout_method && (
                    <span className="px-1.5 py-0.5 rounded-full bg-[#F2EFE8] text-[#2E5C46] border border-[#D7CFB8]">
                      via {e.payout_method}
                    </span>
                  )}
                  {e.payout_reference && (
                    <span className="px-1.5 py-0.5 rounded-full bg-white text-[#1A2424] border border-[#E5E1D8] font-mono normal-case tracking-normal">
                      ref&nbsp;{e.payout_reference}
                    </span>
                  )}
                </div>
              )}
              {e.status === "paid" && e.payout_note && (
                <p className="text-[11px] text-[#5C6B6B] italic mt-1.5 leading-snug" data-testid={`paid-note-${e.id}`}>
                  {e.payout_note}
                </p>
              )}
            </div>
            <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium shrink-0 ${e.status === "paid" ? "bg-[#2E5C46] text-white" : "bg-[#C9A961] text-[#1A2424]"}`}>{e.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function W9Tab({ w9, form, setForm, onSaved }) {
  const [saving, setSaving] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put("/me/payouts/w9", form);
      toast.success("W9 saved.");
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed.");
    } finally { setSaving(false); }
  };
  return (
    <form onSubmit={submit} className="mt-6 card p-6 max-w-2xl" data-testid="w9-form">
      {w9 && w9.signed_at && (
        <div className="mb-4 p-3 bg-[#FFFBEF] rounded text-xs text-[#8B7128] inline-flex items-center gap-1">
          <CheckCircle2 size={12} /> W9 on file (signed {new Date(w9.signed_at).toLocaleDateString()}). Tin on file: <strong>{w9.tin_masked}</strong>. Submitting again will replace.
        </div>
      )}
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label="Full legal name *" v={form.full_name} onChange={(v) => setForm({ ...form, full_name: v })} testid="w9-name" />
        <Field label="Business name (if different)" v={form.business_name || ""} onChange={(v) => setForm({ ...form, business_name: v })} testid="w9-business" />
      </div>
      <div className="mt-3">
        <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Federal tax classification *</label>
        <select value={form.classification} onChange={(e) => setForm({ ...form, classification: e.target.value })} className="input-field w-full text-sm" data-testid="w9-classification">
          {CLASSIFICATIONS.map((c) => <option key={c.v} value={c.v}>{c.l}</option>)}
        </select>
      </div>
      <Field label="Exempt payee code (rare — leave blank if you don't know)" v={form.exempt_payee_code || ""} onChange={(v) => setForm({ ...form, exempt_payee_code: v })} testid="w9-exempt" />
      <Field label="Address line 1 *" v={form.address_line1} onChange={(v) => setForm({ ...form, address_line1: v })} testid="w9-addr1" />
      <Field label="Address line 2" v={form.address_line2 || ""} onChange={(v) => setForm({ ...form, address_line2: v })} testid="w9-addr2" />
      <div className="grid grid-cols-3 gap-3">
        <Field label="City *" v={form.city} onChange={(v) => setForm({ ...form, city: v })} testid="w9-city" />
        <Field label="State *" v={form.state} onChange={(v) => setForm({ ...form, state: v })} testid="w9-state" />
        <Field label="ZIP *" v={form.zip_code} onChange={(v) => setForm({ ...form, zip_code: v })} testid="w9-zip" />
      </div>
      <div className="grid grid-cols-3 gap-3 mt-3">
        <div>
          <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">TIN type *</label>
          <select value={form.tin_type} onChange={(e) => setForm({ ...form, tin_type: e.target.value })} className="input-field w-full text-sm" data-testid="w9-tin-type">
            <option value="SSN">SSN</option>
            <option value="EIN">EIN</option>
          </select>
        </div>
        <Field label={`${form.tin_type} *`} v={form.tin} onChange={(v) => setForm({ ...form, tin: v })} testid="w9-tin" placeholder="9 digits" />
        <Field label="Country" v={form.country} onChange={(v) => setForm({ ...form, country: v })} testid="w9-country" />
      </div>
      <Field label="I attest the above is true (type full name) *" v={form.signature_name} onChange={(v) => setForm({ ...form, signature_name: v })} testid="w9-signature" />
      <button type="submit" disabled={saving} className="btn-primary mt-5" data-testid="w9-save">{saving ? "Saving..." : "Save & sign"}</button>
    </form>
  );
}

function MethodTab({ method, form, setForm, onSaved }) {
  const [saving, setSaving] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { method_type: form.method_type };
      if (form.method_type === "stripe_connect") {
        payload.stripe_account_id = form.stripe_account_id;
      } else {
        payload.bank_name = form.bank_name;
        payload.account_holder_name = form.account_holder_name;
        payload.routing_number = form.routing_number;
        payload.account_number = form.account_number;
      }
      await api.put("/me/payouts/method", payload);
      toast.success("Payout method saved.");
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed.");
    } finally { setSaving(false); }
  };
  return (
    <form onSubmit={submit} className="mt-6 card p-6 max-w-2xl" data-testid="method-form">
      {method && (
        <div className="mb-4 p-3 bg-[#FFFBEF] rounded text-xs text-[#8B7128]">
          Current method: <strong>{method.method_type}</strong>
          {method.method_type === "stripe_connect" && <> · Account: <code>{method.stripe_account_id}</code></>}
          {method.method_type === "manual_ach" && <> · {method.bank_name} · ending in <strong>{method.account_number_last4}</strong></>}
        </div>
      )}
      <div>
        <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Method type *</label>
        <select value={form.method_type} onChange={(e) => setForm({ ...form, method_type: e.target.value })} className="input-field w-full text-sm" data-testid="method-type">
          <option value="stripe_connect">Stripe Connect (preferred)</option>
          <option value="manual_ach">Manual ACH</option>
        </select>
      </div>
      {form.method_type === "stripe_connect" ? (
        <Field label="Stripe Connect account ID *" v={form.stripe_account_id} onChange={(v) => setForm({ ...form, stripe_account_id: v })} placeholder="acct_..." testid="method-stripe-acct" />
      ) : (
        <div className="space-y-3 mt-3">
          <Field label="Bank name *" v={form.bank_name} onChange={(v) => setForm({ ...form, bank_name: v })} testid="method-bank" />
          <Field label="Account holder name *" v={form.account_holder_name} onChange={(v) => setForm({ ...form, account_holder_name: v })} testid="method-holder" />
          <Field label="Routing number (9 digits) *" v={form.routing_number} onChange={(v) => setForm({ ...form, routing_number: v })} testid="method-routing" />
          <Field label="Account number *" v={form.account_number} onChange={(v) => setForm({ ...form, account_number: v })} testid="method-account" />
          <p className="text-[10px] text-[#5C6B6B]">Account number is encrypted at rest. Only the last 4 digits are visible after save.</p>
        </div>
      )}
      <button type="submit" disabled={saving} className="btn-primary mt-5" data-testid="method-save">{saving ? "Saving..." : "Save method"}</button>
    </form>
  );
}

function Stat({ label, value, testid }) {
  return (
    <div className="card p-4" data-testid={testid}>
      <p className="label text-[10px]">{label}</p>
      <p className="font-serif text-2xl text-[#1A2424] mt-1">{value}</p>
    </div>
  );
}
function Field({ label, v, onChange, placeholder, testid }) {
  return (
    <div className="mt-3">
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <input value={v || ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
