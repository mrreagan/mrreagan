import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { BrandLogo } from "../components/BrandLogo";
import { toast } from "sonner";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "", password: "", accepted_terms: false, accepted_privacy: false });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.accepted_terms || !form.accepted_privacy) {
      toast.error("Please accept the Terms of Service and Privacy Policy to continue.");
      return;
    }
    setLoading(true);
    try {
      await register(form);
      toast.success("Welcome to birthright");
      const next = new URLSearchParams(location.search).get("next");
      navigate(next || "/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-20 max-w-md mx-auto" data-testid="register-page">
      <div className="text-center mb-8">
        <BrandLogo size="lg" className="justify-center" />
      </div>
      <div className="card p-8">
        <span className="label">Begin here</span>
        <h1 className="font-serif text-3xl mt-2">Create your account</h1>
        <form onSubmit={submit} className="mt-6 space-y-4" data-testid="register-form">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label block mb-2">First Name</label>
              <input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className="input-field" data-testid="register-first-name" />
            </div>
            <div>
              <label className="label block mb-2">Last Name</label>
              <input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} className="input-field" data-testid="register-last-name" />
            </div>
          </div>
          <div>
            <label className="label block mb-2">Email</label>
            <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input-field" data-testid="register-email" />
          </div>
          <div>
            <label className="label block mb-2">Phone (optional)</label>
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" data-testid="register-phone" />
          </div>
          <div>
            <label className="label block mb-2">Password (min 6)</label>
            <input required type="password" minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="input-field" data-testid="register-password" />
          </div>

          {/* Consent checkboxes — required. Backend enforces both flags true. */}
          <div className="space-y-2 pt-2 border-t border-[#E8E4DC]">
            <label className="flex items-start gap-2 cursor-pointer text-xs text-[#3D4A4A] leading-relaxed">
              <input
                type="checkbox"
                checked={form.accepted_terms}
                onChange={(e) => setForm({ ...form, accepted_terms: e.target.checked })}
                className="mt-0.5 h-4 w-4 accent-[#C9A961]"
                data-testid="register-accept-terms"
                required
              />
              <span>
                I have read and agree to the{" "}
                <Link to="/legal/terms" target="_blank" className="underline text-[#476B6B] hover:text-[#0F2424]">
                  Terms of Service
                </Link>.
              </span>
            </label>
            <label className="flex items-start gap-2 cursor-pointer text-xs text-[#3D4A4A] leading-relaxed">
              <input
                type="checkbox"
                checked={form.accepted_privacy}
                onChange={(e) => setForm({ ...form, accepted_privacy: e.target.checked })}
                className="mt-0.5 h-4 w-4 accent-[#C9A961]"
                data-testid="register-accept-privacy"
                required
              />
              <span>
                I have read and agree to the{" "}
                <Link to="/legal/privacy" target="_blank" className="underline text-[#476B6B] hover:text-[#0F2424]">
                  Privacy Policy
                </Link>{" "}
                (including logging of IP address, session activity, and 365-day retention of security-audit records).
              </span>
            </label>
          </div>

          <button type="submit" disabled={loading || !form.accepted_terms || !form.accepted_privacy} className="btn-primary w-full justify-center" data-testid="register-submit">
            {loading ? "Creating..." : "Create account"}
          </button>
        </form>
        <p className="text-sm text-[#5C6B6B] mt-6 text-center">
          Already have an account?{" "}
          <Link to="/login" className="text-[#476B6B] font-medium hover:underline" data-testid="register-to-login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
