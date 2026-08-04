/**
 * AdminCounselSettings — rotate the counsel email + password from the UI.
 *
 * Route: /admin/settings/counsel
 *
 * The env vars COUNSEL_EMAIL / COUNSEL_PASSWORD are used only for the
 * initial bootstrap. Once the account exists in Mongo the DB is the
 * source of truth — that's what this page edits. Any change here
 * persists across redeploys.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Briefcase, KeyRound, Save, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";

export default function AdminCounselSettings() {
  const [state, setState] = useState(null);
  const [form, setForm] = useState({ email: "", password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [sendingLink, setSendingLink] = useState(false);

  const sendSetPasswordLink = async () => {
    if (!window.confirm(`Email a one-time set-password link to ${state?.email}? Any older unused link is superseded.`)) return;
    setSendingLink(true);
    try {
      const r = await api.post("/admin/settings/counsel/send-set-password-link");
      toast.success(`Set-password link emailed to ${r.data.email_sent_to}. Expires in 24 hours.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not send link");
    } finally {
      setSendingLink(false);
    }
  };

  const load = async () => {
    try {
      const r = await api.get("/admin/settings/counsel");
      setState(r.data);
      setForm((f) => ({ ...f, email: r.data.email || "" }));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load counsel settings");
    }
  };

  useEffect(() => { load(); }, []);

  const rotate = async () => {
    const emailChanged = state && form.email !== state.email;
    const wantPwChange = !!form.password;
    if (!emailChanged && !wantPwChange) {
      toast.error("Change the email or set a new password first.");
      return;
    }
    if (wantPwChange) {
      if (form.password.length < 12) { toast.error("Password must be at least 12 characters."); return; }
      if (form.password !== form.confirm) { toast.error("Passwords don't match."); return; }
    }
    const payload = {};
    if (emailChanged) payload.email = form.email.trim();
    if (wantPwChange) payload.password = form.password;

    setBusy(true);
    try {
      const r = await api.post("/admin/settings/counsel/rotate", payload);
      const bits = [];
      if (emailChanged) bits.push(`email → ${r.data.email}`);
      if (r.data.password_changed) bits.push("password rotated");
      toast.success(`Counsel credentials updated: ${bits.join(" · ")}`);
      setForm({ email: r.data.email, password: "", confirm: "" });
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Rotate failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container-page py-12 max-w-2xl" data-testid="admin-counsel-settings-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <div className="mt-4">
        <span className="label block">Settings · Counsel</span>
        <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
          <Briefcase size={26} strokeWidth={1.2} /> Counsel credentials
        </h1>
      </div>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Rotate the read-only counsel account&apos;s email and password. Env
        vars are only used to seed the account the first time — after that,
        this page is the source of truth and changes persist across redeploys.
      </p>

      {!state ? (
        <p className="mt-6 text-sm text-[#5C6B6B]">Loading…</p>
      ) : (
        <>
          <div className="card p-5 mt-8" data-testid="counsel-current-state">
            <p className="text-[10px] uppercase tracking-wider text-[#476B6B] font-semibold">Current</p>
            <p className="text-sm mt-1">
              <span className="text-[#5C6B6B]">Email:</span>{" "}
              <span className="font-mono text-[#0F2424]" data-testid="counsel-current-email">{state.email}</span>
            </p>
            {state.last_rotated_at && (
              <p className="text-xs text-[#5C6B6B] mt-1" data-testid="counsel-last-rotated">
                Last rotated {new Date(state.last_rotated_at).toLocaleString()}
                {state.last_rotated_by ? ` by ${state.last_rotated_by}` : ""}
              </p>
            )}
            {state.env_password_default_in_use && (
              <p className="text-xs text-[#7A5A1A] mt-2 bg-[#FFF6E3] border-l-2 border-[#C9A961] pl-2 py-1" data-testid="counsel-env-warning">
                Password still matches the env default (<code>counsel-review-2026</code>). Rotate it before sharing the account with real outside counsel.
              </p>
            )}
          </div>

          <div className="card p-5 mt-5" data-testid="counsel-send-link-card">
            <p className="text-[10px] uppercase tracking-wider text-[#476B6B] font-semibold inline-flex items-center gap-1">
              <Send size={12} /> Recommended · Let counsel choose their own password
            </p>
            <p className="text-xs text-[#5C6B6B] mt-1 leading-relaxed">
              Emails <strong>{state.email}</strong> a one-time link (valid 24 h) so counsel can set their own password. You never see or type the plaintext. Any older unused link is superseded.
            </p>
            <button
              onClick={sendSetPasswordLink}
              disabled={sendingLink}
              className="btn-outline text-sm inline-flex items-center gap-1 mt-3"
              data-testid="counsel-send-link-btn"
            >
              {sendingLink ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
              {sendingLink ? "Sending…" : "Send set-password link"}
            </button>
          </div>

          <div className="card p-5 mt-5">
            <p className="text-[10px] uppercase tracking-wider text-[#476B6B] font-semibold">Change email</p>
            <p className="text-xs text-[#5C6B6B] mt-1 leading-relaxed">
              Point this to the address counsel should receive login-related mail at. If you set up Cloudflare Email Routing (e.g. <code>counsel@birthright.live</code> → counsel&apos;s firm inbox), use the routed address here so their firm email stays out of the audit log.
            </p>
            <input
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="counsel@birthright.live"
              className="input input-bordered w-full text-sm mt-3"
              data-testid="counsel-new-email"
            />
          </div>

          <div className="card p-5 mt-5">
            <p className="text-[10px] uppercase tracking-wider text-[#476B6B] font-semibold inline-flex items-center gap-1">
              <KeyRound size={12} /> Change password
            </p>
            <p className="text-xs text-[#5C6B6B] mt-1 leading-relaxed">
              Leave blank to keep the current password. Minimum 12 characters. Any active counsel session is invalidated on rotation.
            </p>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="New password (min 12 chars)"
              className="input input-bordered w-full text-sm mt-3"
              data-testid="counsel-new-password"
              autoComplete="new-password"
            />
            <input
              type="password"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              placeholder="Confirm new password"
              className="input input-bordered w-full text-sm mt-2"
              data-testid="counsel-confirm-password"
              autoComplete="new-password"
            />
          </div>

          <div className="flex items-center gap-2 mt-6">
            <button
              onClick={rotate}
              disabled={busy}
              className="btn-primary text-sm inline-flex items-center gap-1"
              data-testid="counsel-rotate-submit"
            >
              {busy ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
              {busy ? "Rotating…" : "Rotate credentials"}
            </button>
            <button
              onClick={() => { setForm({ email: state.email, password: "", confirm: "" }); }}
              className="btn-ghost text-xs"
              data-testid="counsel-rotate-reset"
            >
              Reset form
            </button>
          </div>

          <p className="mt-6 text-[11px] text-[#5C6B6B] leading-relaxed">
            Tip: If you rotated the email, the previous address stops working immediately. Send the new credentials to counsel over a secure channel — this app does not automatically email the new password.
          </p>
        </>
      )}
    </div>
  );
}
