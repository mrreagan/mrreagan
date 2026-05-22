import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    phone: user?.phone || "",
    bio: user?.bio || "",
    avatar_url: user?.avatar_url || "",
  });
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.put("/auth/me", form);
      await refreshUser();
      toast.success("Profile saved");
    } catch (err) {
      toast.error("Could not save");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-16 max-w-2xl" data-testid="profile-page">
      <span className="label">Profile</span>
      <h1 className="editorial-h1 mt-2">Your account</h1>
      <div className="divider-flame" />

      <form onSubmit={submit} className="card p-7 mt-8 space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label block mb-2">First Name</label>
            <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className="input-field" data-testid="profile-first-name" />
          </div>
          <div>
            <label className="label block mb-2">Last Name</label>
            <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} className="input-field" data-testid="profile-last-name" />
          </div>
        </div>
        <div>
          <label className="label block mb-2">Email</label>
          <input value={user?.email} disabled className="input-field opacity-60" />
        </div>
        <div>
          <label className="label block mb-2">Phone</label>
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" data-testid="profile-phone" />
        </div>
        <div>
          <label className="label block mb-2">Bio</label>
          <textarea rows={4} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="input-field resize-none" data-testid="profile-bio" />
        </div>
        <div>
          <label className="label block mb-2">Avatar URL</label>
          <input value={form.avatar_url} onChange={(e) => setForm({ ...form, avatar_url: e.target.value })} className="input-field" data-testid="profile-avatar" />
        </div>
        <button type="submit" disabled={loading} className="btn-primary justify-center" data-testid="profile-submit">
          {loading ? "Saving..." : "Save changes"}
        </button>
      </form>
    </div>
  );
}
