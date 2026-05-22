import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "../lib/api";
import { BrandLogo } from "../components/BrandLogo";
import { toast } from "sonner";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!token) {
      toast.error("Missing or invalid reset token");
      return;
    }
    if (pw.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    if (pw !== pw2) {
      toast.error("Passwords don't match");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      toast.success("Password updated. Please sign in.");
      navigate("/login");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-20 max-w-md mx-auto" data-testid="reset-password-page">
      <div className="text-center mb-8">
        <BrandLogo size="lg" className="justify-center" />
      </div>
      <div className="card p-8">
        <span className="label">Account recovery</span>
        <h1 className="font-serif text-3xl mt-2">New password</h1>
        {!token ? (
          <div className="mt-6">
            <p className="text-sm text-[#1A2424]">This link is missing its reset token.</p>
            <Link to="/forgot-password" className="btn-outline w-full justify-center mt-4">Start over</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-5" data-testid="reset-form">
            <div>
              <label className="label block mb-2">New password</label>
              <input
                type="password"
                required minLength={6}
                value={pw} onChange={(e) => setPw(e.target.value)}
                className="input-field"
                data-testid="reset-password-1"
              />
            </div>
            <div>
              <label className="label block mb-2">Confirm new password</label>
              <input
                type="password"
                required minLength={6}
                value={pw2} onChange={(e) => setPw2(e.target.value)}
                className="input-field"
                data-testid="reset-password-2"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center" data-testid="reset-submit">
              {loading ? "Saving..." : "Set new password"}
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
