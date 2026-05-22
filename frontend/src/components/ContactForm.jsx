import React, { useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";

const initialForm = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  subject: "",
  message: "",
  newsletter_opt_in: true,
};

export default function ContactForm() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);

  const handleChange = (field) => (e) => {
    const value = field === "newsletter_opt_in" ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/contact", form);
      toast.success(data.message || "Message received.");
      setForm(initialForm);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send message.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="lg:col-span-6 lg:col-start-7">
      <form onSubmit={submit} className="card p-8 space-y-5" data-testid="contact-form">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="First Name" required value={form.first_name} onChange={handleChange("first_name")} testId="contact-first-name" />
          <Field label="Last Name" value={form.last_name} onChange={handleChange("last_name")} testId="contact-last-name" />
        </div>
        <Field label="Email" required type="email" mandatory value={form.email} onChange={handleChange("email")} testId="contact-email" />
        <Field label="Phone / Mobile" value={form.phone} onChange={handleChange("phone")} testId="contact-phone" />
        <Field label="Subject" value={form.subject} onChange={handleChange("subject")} placeholder="e.g., Workshop inquiry, Sponsorship" testId="contact-subject" />
        <TextAreaField label="Your Message" required mandatory value={form.message} onChange={handleChange("message")} testId="contact-message" />
        <label className="flex items-center gap-3 text-sm text-[#1A2424] cursor-pointer">
          <input
            type="checkbox"
            checked={form.newsletter_opt_in}
            onChange={handleChange("newsletter_opt_in")}
            className="w-4 h-4 accent-[#476B6B]"
            data-testid="contact-newsletter-opt-in"
          />
          Yes, I'd like to receive occasional updates from birthright.
        </label>
        <button type="submit" disabled={loading} className="btn-primary w-full justify-center" data-testid="contact-submit">
          {loading ? "Sending..." : "Send message"}
        </button>
      </form>
    </div>
  );
}

function Field({ label, required, mandatory, type = "text", value, onChange, placeholder, testId }) {
  return (
    <div>
      <label className="label block mb-2">
        {label} {mandatory && <span className="text-[#9E3C3C]">*</span>}
      </label>
      <input
        required={required}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="input-field"
        data-testid={testId}
      />
    </div>
  );
}

function TextAreaField({ label, required, mandatory, value, onChange, testId }) {
  return (
    <div>
      <label className="label block mb-2">
        {label} {mandatory && <span className="text-[#9E3C3C]">*</span>}
      </label>
      <textarea
        required={required}
        rows={6}
        value={value}
        onChange={onChange}
        className="input-field resize-none"
        data-testid={testId}
      />
    </div>
  );
}
