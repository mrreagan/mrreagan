import React, { useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Mail } from "lucide-react";

export function NewsletterSignup({ compact = false }) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      const { data } = await api.post("/newsletter", { email });
      toast.success(data.message || "Subscribed!");
      setEmail("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not subscribe.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className={`flex ${compact ? "gap-2" : "flex-col sm:flex-row gap-3"}`}
      data-testid="newsletter-form"
    >
      <div className="flex items-center gap-2 input-field flex-1 !py-2">
        <Mail size={16} strokeWidth={1.5} className="text-[#5C6B6B] shrink-0" />
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="bg-transparent outline-none flex-1 text-sm"
          data-testid="newsletter-email-input"
        />
      </div>
      <button type="submit" disabled={loading} className="btn-primary justify-center" data-testid="newsletter-submit">
        {loading ? "..." : "Subscribe"}
      </button>
    </form>
  );
}

export default NewsletterSignup;
