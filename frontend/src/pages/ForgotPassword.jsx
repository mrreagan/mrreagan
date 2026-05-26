import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { BrandLogo } from "../components/BrandLogo";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [dryRunUrl, setDryRunUrl] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post("/auth/request-password-reset", { email });
      setSent(true);
      if (res.data?.dry_run && res.data?.reset_url) {
        setDryRunUrl(res.data.reset_url);
        toast.success("Reset link generated (dev mode)");
      } else {
        toast.success(res.data?.message || "Check your inbox");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-20 max-w-md mx-auto" data-testid="forgot-password-page">
      <div className="text-center mb-8">
        <BrandLogo size="lg" className="justify-center" />
      </div>
      <div className="card p-8">
        <span className="label">Account recovery</span>
        <h1 className="font-serif text-3xl mt-2">Reset password</h1>
        {sent ? (
          <div className="mt-6" data-testid="forgot-sent">
            {dryRunUrl ? (
              <div className="rounded-xl border-2 border-[#C9A961] bg-[#FFF8E1] p-4" data-testid="forgot-dryrun-card">
                <p className="text-[10px] uppercase tracking-wider text-[#8B7128] font-semibold">
                  Email in dry-run mode
                </p>
                <p className="text-sm text-[#1A2424] mt-2 leading-relaxed">
                  We haven't enabled live email delivery yet (no Resend API key on this environment).
                  Use the link below to reset your password directly — it expires in one hour.
                </p>
                <a
                  href={dryRunUrl}
                  className="btn-primary w-full justify-center mt-4 text-sm"
                  data-testid="forgot-dryrun-link"
                >
                  Reset password now →
                </a>
                <p className="text-[10px] text-[#5C6B6B] mt-3 break-all">
                  {dryRunUrl}
                </p>
              </div>
            ) : (
              <>
                <p className="text-sm text-[#1A2424] leading-relaxed">
                  If <span className="font-medium">{email}</span> is registered, a reset link is on its way. It expires in one hour.
                </p>
                <p className="text-xs text-[#5C6B6B] mt-4">
                  Didn't get it after a few minutes? Check spam, or try again with the right address.
                </p>
              </>
            )}
            <Link to="/login" className="btn-outline w-full justify-center mt-6" data-testid="forgot-back-login">
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-5" data-testid="forgot-form">
            <p className="text-sm text-[#5C6B6B] leading-relaxed">
              Enter the email you used to register. We'll send you a one-hour reset link.
            </p>
            <div>
              <label className="label block mb-2">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                data-testid="forgot-email"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center" data-testid="forgot-submit">
              {loading ? "Sending..." : "Send reset link"}
            </button>
            <p className="text-xs text-[#5C6B6B] text-center">
              <Link to="/login" className="hover:text-[#476B6B]">Back to sign in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
