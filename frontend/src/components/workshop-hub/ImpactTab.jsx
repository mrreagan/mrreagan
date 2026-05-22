import React, { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";

const initialForm = {
  what_learned: "",
  how_grew: "",
  benefits: "",
  improvements: "",
  is_public: false,
  anonymous: false,
};

function SuccessConfirmation() {
  return (
    <div className="card p-8 mt-6 text-center">
      <CheckCircle2 size={36} strokeWidth={1.5} className="text-[#2E5C46] mx-auto" />
      <p className="text-sm text-[#1A2424] mt-3">Saved. You can edit it anytime from your dashboard.</p>
    </div>
  );
}

function TextField({ label, required, value, onChange, testId }) {
  return (
    <div>
      <label className="label block mb-2">{label}</label>
      <textarea
        required={required}
        rows={3}
        value={value}
        onChange={onChange}
        className="input-field resize-none"
        data-testid={testId}
      />
    </div>
  );
}

function SharingToggles({ form, onUpdate }) {
  return (
    <div className="space-y-2 pt-2 border-t border-[#E5E1D8]">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.is_public}
          onChange={(e) => onUpdate("is_public", e.target.checked)}
          className="accent-[#476B6B]"
          data-testid="impact-public"
        />
        Share publicly on the homepage and workshop page (optional)
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.anonymous}
          onChange={(e) => onUpdate("anonymous", e.target.checked)}
          className="accent-[#476B6B]"
          data-testid="impact-anonymous"
        />
        Share anonymously
      </label>
    </div>
  );
}

export default function ImpactTab({ workshop }) {
  const [form, setForm] = useState(initialForm);
  const [submitted, setSubmitted] = useState(false);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/impact-statements", { ...form, workshop_id: workshop.id });
      setSubmitted(true);
      toast.success("Thank you for sharing.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit");
    }
  };

  return (
    <div className="max-w-3xl" data-testid="tab-impact">
      <span className="label">Personal impact statement</span>
      <h3 className="font-serif text-2xl mt-2">Reflect on your experience.</h3>
      <p className="text-sm text-[#5C6B6B] mt-2">
        For yourself, and — if you choose — for the people considering this workshop.
      </p>
      {submitted ? (
        <SuccessConfirmation />
      ) : (
        <form onSubmit={submit} className="card p-7 mt-6 space-y-5">
          <TextField label="What I learned" required value={form.what_learned} onChange={(e) => update("what_learned", e.target.value)} testId="impact-learned" />
          <TextField label="How I grew" required value={form.how_grew} onChange={(e) => update("how_grew", e.target.value)} testId="impact-grew" />
          <TextField label="How I benefited" required value={form.benefits} onChange={(e) => update("benefits", e.target.value)} testId="impact-benefits" />
          <TextField label="Ideas to improve (optional)" value={form.improvements} onChange={(e) => update("improvements", e.target.value)} testId="impact-improvements" />
          <SharingToggles form={form} onUpdate={update} />
          <button type="submit" className="btn-primary w-full justify-center" data-testid="impact-submit">
            Save my impact statement
          </button>
        </form>
      )}
    </div>
  );
}
