/**
 * CounselSetPasswordPage — one-time self-service password setter.
 *
 * Route: /counsel/set-password?token=<opaque-token>
 *
 * Reached from the "Set your password" email that admin triggers on the
 * /admin/settings/counsel page. The token is short-lived (24h) and
 * one-time-use — a successful submit invalidates every current counsel
 * JWT so the newly-set password is the ONLY way to sign in.
 */
import React, { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { KeyRound, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";

export default function CounselSetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (pw.length < 12) { toast.error("Password must be at least 12 characters."); return; }
    if (pw !== confirm) { toast.error("Passwords don't match."); return; }
    setBusy(true);
    try {
      const r = await api.post("/admin/settings/counsel/set-password-from-token", { token, password: pw });
      setDone(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not set password. The link may have expired.");
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="container-page py-16 max-w-md" data-testid="counsel-set-password-missing">
        <p className="text-sm text-[#9E3C3C]">This link is missing its token. Ask admin to send you a fresh set-password email.</p>
      </div>
    );
  }

  if (done) {
    return (
      <div className="container-page py-16 max-w-md" data-testid="counsel-set-password-done">
        <span className="label block">Counsel</span>
        <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
          <CheckCircle2 size={26} strokeWidth={1.2} className="text-[#2E5C46]" /> Password set
        </h1>
        <div className="divider-flame" />
        <p className="text-sm text-[#0F2424] mt-3">
          You can now sign in at&nbsp;
          <Link to="/login" className="underline text-[#476B6B]" data-testid="counsel-set-password-signin-link">
            /login
          </Link>
          &nbsp;using <strong>{done.email}</strong>.
        </p>
      </div>
    );
  }

  return (
    <div className="container-page py-16 max-w-md" data-testid="counsel-set-password-page">
      <span className="label block">Counsel</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <KeyRound size={26} strokeWidth={1.2} /> Set your password
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B]">
        This link works once and expires in 24 hours from the time it was sent.
        Pick a password of at least 12 characters.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-3" data-testid="counsel-set-password-form">
        <input
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="New password (min 12 chars)"
          className="input input-bordered w-full text-sm"
          autoComplete="new-password"
          data-testid="counsel-set-password-input"
        />
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Confirm new password"
          className="input input-bordered w-full text-sm"
          autoComplete="new-password"
          data-testid="counsel-set-password-confirm"
        />
        <button type="submit" disabled={busy} className="btn-primary text-sm" data-testid="counsel-set-password-submit">
          {busy ? "Saving…" : "Set password"}
        </button>
      </form>
    </div>
  );
}
