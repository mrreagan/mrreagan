import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { BrandLogo } from "../components/BrandLogo";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      const dest = location.state?.from || "/dashboard";
      navigate(dest);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-20 max-w-md mx-auto" data-testid="login-page">
      <div className="text-center mb-8">
        <BrandLogo size="lg" className="justify-center" />
      </div>
      <div className="card p-8">
        <span className="label">Welcome back</span>
        <h1 className="font-serif text-3xl mt-2">Sign in</h1>
        <form onSubmit={submit} className="mt-6 space-y-5" data-testid="login-form">
          <div>
            <label className="label block mb-2">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" data-testid="login-email" />
          </div>
          <div>
            <label className="label block mb-2">Password</label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" data-testid="login-password" />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full justify-center" data-testid="login-submit">
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="text-xs text-[#5C6B6B] mt-4 text-center">
          <Link to="/forgot-password" className="hover:text-[#476B6B]" data-testid="login-forgot-link">
            Forgot your password?
          </Link>
        </p>
        <p className="text-sm text-[#5C6B6B] mt-6 text-center">
          New here?{" "}
          <Link to="/register" className="text-[#476B6B] font-medium hover:underline" data-testid="login-to-register">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
