import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../lib/api";
import { ArrowLeft, Heart, Clock, CheckCircle2 } from "lucide-react";
import ShareButton from "../components/ShareButton";

export default function JoinUsRole() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    current_role: "",
    why_drawn: "",
    resume_url: "",
    linkedin_url: "",
    phone: "",
  });

  useEffect(() => {
    api.get(`/foundation-roles/${slug}`)
      .then((r) => setRole(r.data))
      .catch(() => navigate("/join-us"))
      .finally(() => setLoading(false));
  }, [slug, navigate]);

  const handleChange = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.why_drawn.trim().length < 20) {
      toast.error("Please tell us at least a few sentences about why you're drawn to this work.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/foundation-role-applications", {
        role_slug: slug,
        name: form.name,
        email: form.email,
        current_role: form.current_role,
        why_drawn: form.why_drawn,
        resume_url: form.resume_url || null,
        linkedin_url: form.linkedin_url || null,
        phone: form.phone || null,
      });
      setSubmitted(true);
      toast.success("Application received. We'll be in touch within two weeks.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Application failed. Try again?");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="container-page py-20">Loading...</div>;
  if (!role) return null;

  if (submitted) {
    return (
      <div className="container-page py-20" data-testid="join-us-thank-you">
        <div className="max-w-xl mx-auto card p-10 text-center">
          <CheckCircle2 size={48} strokeWidth={1.5} className="text-[#2E5C46] mx-auto" />
          <h1 className="font-serif text-3xl mt-4">Thank you.</h1>
          <p className="text-base text-[#5C6B6B] mt-4 leading-relaxed">
            We've received your application for the <strong>{role.title}</strong> role. A member of
            the governing board will be in touch within two weeks. A confirmation email is on its
            way to <strong>{form.email}</strong>.
          </p>
          <Link to="/join-us" className="btn-outline inline-flex items-center gap-2 mt-6" data-testid="back-to-roles">
            <ArrowLeft size={14} strokeWidth={1.5} /> Back to open roles
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container-page py-12" data-testid="join-us-role-page">
      <Link to="/join-us" className="inline-flex items-center gap-1 text-sm text-[#476B6B] hover:underline" data-testid="back-link">
        <ArrowLeft size={14} strokeWidth={1.5} /> All open roles
      </Link>

      <div className="grid lg:grid-cols-5 gap-10 mt-6">
        <div className="lg:col-span-3">
          <div className="flex flex-wrap items-start gap-3 mb-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-medium bg-[#476B6B] text-white">
              Open Role
            </span>
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-medium bg-[#2E5C46] text-white">
              <Heart size={10} strokeWidth={2} /> Equity in Mission
            </span>
            {role.time_commitment && (
              <span className="inline-flex items-center gap-1 text-xs text-[#5C6B6B]">
                <Clock size={12} strokeWidth={1.5} />
                {role.time_commitment}
              </span>
            )}
          </div>
          <h1 className="editorial-h1" data-testid="role-detail-title">{role.title}</h1>
          <p className="text-lg text-[#476B6B] mt-3 leading-snug">{role.headline}</p>
          <div className="mt-4">
            <ShareButton
              surface="foundation_role"
              surfaceId={role.slug}
              path={`/join-us/${role.slug}`}
              title={role.title}
              emailSubject={`Open role at Birthright: ${role.title}`}
              showLabel
              align="left"
            />
          </div>

          <div className="mt-8 space-y-6">
            <Section title="Who you are" body={role.who_you_are} />
            <Section title="What you'll do" body={role.what_youll_do} />
            <Section title="What you bring" body={role.what_you_bring} />
          </div>

          <div className="mt-8 p-5 rounded-lg bg-[#FFFBEF] border-l-4 border-[#C9A961]">
            <p className="label text-[#8B7128]">Compensation</p>
            <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">{role.compensation_summary}</p>
          </div>
        </div>

        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="card p-6 lg:sticky lg:top-24" data-testid="apply-form">
            <h2 className="font-serif text-2xl">Apply</h2>
            <p className="text-xs text-[#5C6B6B] mt-1">No account required.</p>

            <div className="mt-5 space-y-4">
              <Field label="Full name" value={form.name} onChange={handleChange("name")} required testid="apply-name" />
              <Field label="Email" type="email" value={form.email} onChange={handleChange("email")} required testid="apply-email" />
              <Field label="Current role / professional title" value={form.current_role} onChange={handleChange("current_role")} testid="apply-current-role" />

              <div>
                <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">
                  Why are you drawn to this work? <span className="text-[#9E3C3C]">*</span>
                </label>
                <textarea
                  value={form.why_drawn}
                  onChange={handleChange("why_drawn")}
                  required
                  rows={5}
                  className="input-field w-full text-sm"
                  placeholder="A few sentences about what draws you to the foundation and to this role specifically."
                  data-testid="apply-why-drawn"
                />
              </div>

              <Field label="Résumé / CV URL (optional)" value={form.resume_url} onChange={handleChange("resume_url")} placeholder="https://..." testid="apply-resume" />
              <Field label="LinkedIn URL (optional)" value={form.linkedin_url} onChange={handleChange("linkedin_url")} placeholder="https://..." testid="apply-linkedin" />
              <Field label="Phone (optional)" value={form.phone} onChange={handleChange("phone")} testid="apply-phone" />

              <button type="submit" disabled={submitting} className="btn-primary w-full justify-center" data-testid="apply-submit">
                {submitting ? "Sending..." : "Submit application"}
              </button>
              <p className="text-[11px] text-[#5C6B6B] text-center">A member of the board will reach out within two weeks.</p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function Section({ title, body }) {
  return (
    <div>
      <p className="label text-[#8B7128] mb-2">{title}</p>
      <p className="text-base text-[#1A2424] leading-relaxed">{body}</p>
    </div>
  );
}

function Field({ label, value, onChange, required, type = "text", placeholder, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">
        {label}{required && <span className="text-[#9E3C3C]"> *</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        className="input-field w-full text-sm"
        data-testid={testid}
      />
    </div>
  );
}
