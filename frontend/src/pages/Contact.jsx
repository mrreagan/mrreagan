import React, { useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Mail, MapPin, Phone } from "lucide-react";

export default function Contact() {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    subject: "",
    message: "",
    newsletter_opt_in: true,
  });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/contact", form);
      toast.success(data.message || "Message received.");
      setForm({ first_name: "", last_name: "", email: "", phone: "", subject: "", message: "", newsletter_opt_in: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send message.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-20" data-testid="contact-page">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-5">
          <span className="label">Contact</span>
          <h1 className="editorial-h1 mt-3">We'd love to hear from you.</h1>
          <div className="divider-flame" />
          <p className="text-base text-[#5C6B6B] leading-relaxed">
            For workshop inquiries, sponsorship questions, facilitator interest, or anything else — write us. We answer within two business days.
          </p>
          <div className="mt-10 space-y-5">
            <div className="flex items-start gap-4">
              <MapPin size={18} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0" />
              <div>
                <p className="text-xs label text-[#C9A961]">Visit us</p>
                <p className="text-sm text-[#1A2424] mt-1">2148 W Earll Dr<br />Phoenix, AZ 85015</p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <Mail size={18} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0" />
              <div>
                <p className="text-xs label text-[#C9A961]">Email</p>
                <a href="mailto:hello@birthright.live" className="text-sm text-[#1A2424] mt-1 block hover:text-[#476B6B]">hello@birthright.live</a>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <Phone size={18} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0" />
              <div>
                <p className="text-xs label text-[#C9A961]">Phone</p>
                <p className="text-sm text-[#1A2424] mt-1">(602) 330-2650</p>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-6 lg:col-start-7">
          <form onSubmit={submit} className="card p-8 space-y-5" data-testid="contact-form">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label block mb-2">First Name</label>
                <input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className="input-field" data-testid="contact-first-name" />
              </div>
              <div>
                <label className="label block mb-2">Last Name</label>
                <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} className="input-field" data-testid="contact-last-name" />
              </div>
            </div>
            <div>
              <label className="label block mb-2">Email <span className="text-[#9E3C3C]">*</span></label>
              <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input-field" data-testid="contact-email" />
            </div>
            <div>
              <label className="label block mb-2">Phone / Mobile</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" data-testid="contact-phone" />
            </div>
            <div>
              <label className="label block mb-2">Subject</label>
              <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="input-field" placeholder="e.g., Workshop inquiry, Sponsorship" data-testid="contact-subject" />
            </div>
            <div>
              <label className="label block mb-2">Your Message <span className="text-[#9E3C3C]">*</span></label>
              <textarea required rows={6} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="input-field resize-none" data-testid="contact-message" />
            </div>
            <label className="flex items-center gap-3 text-sm text-[#1A2424] cursor-pointer">
              <input
                type="checkbox"
                checked={form.newsletter_opt_in}
                onChange={(e) => setForm({ ...form, newsletter_opt_in: e.target.checked })}
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
      </div>
    </div>
  );
}
