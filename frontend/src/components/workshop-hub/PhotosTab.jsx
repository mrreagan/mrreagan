import React, { useEffect, useRef, useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";
import { Camera, Clock, CheckCircle2, XCircle, Trash2, Upload, ImageOff } from "lucide-react";

function StatusChip({ status }) {
  const map = {
    pending: { bg: "bg-[#C9A961]/15 text-[#C9A961]", icon: Clock, label: "Awaiting review" },
    approved: { bg: "bg-[#2E5C46]/10 text-[#2E5C46]", icon: CheckCircle2, label: "Approved" },
    rejected: { bg: "bg-[#B86A5C]/10 text-[#B86A5C]", icon: XCircle, label: "Not approved" },
  };
  const c = map[status] || map.pending;
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${c.bg}`}>
      <Icon size={10} strokeWidth={2} /> {c.label}
    </span>
  );
}

export default function PhotosTab({ workshop, user }) {
  const [photos, setPhotos] = useState([]);
  const [myPending, setMyPending] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [caption, setCaption] = useState("");
  const fileInputRef = useRef(null);

  const load = async () => {
    try {
      const [approved, all] = await Promise.all([
        api.get(`/workshop-photos/${workshop.id}?status=approved`),
        api.get(`/workshop-photos/${workshop.id}?status=all`),
      ]);
      setPhotos(approved.data);
      setMyPending(all.data.filter((p) => p.uploader_id === user.id && p.status !== "approved"));
    } catch (err) {
      console.error("Failed to load photos:", err);
    }
  };
  useEffect(() => { load(); }, [workshop.id, user.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      toast.error("File too large (max 8 MB)");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    fd.append("caption", caption);
    setUploading(true);
    try {
      await api.post(`/workshop-photos/${workshop.id}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const role = user.role;
      toast.success(role === "facilitator" || role === "admin"
        ? "Photo posted to the gallery."
        : "Photo uploaded. A facilitator will review it shortly.");
      setCaption("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const removeMyPhoto = async (photo) => {
    if (!window.confirm("Remove this photo?")) return;
    try {
      await api.delete(`/workshop-photos/${photo.id}`);
      toast.success("Photo removed");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not delete");
    }
  };

  return (
    <div className="space-y-8" data-testid="hub-photos-tab">
      <div className="card p-6">
        <div className="flex items-center gap-2">
          <Camera size={18} strokeWidth={1.5} className="text-[#C9A961]" />
          <h3 className="font-serif text-xl">Share a moment</h3>
        </div>
        <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
          Upload a photo from this workshop. Participant uploads are reviewed by a facilitator before they appear in the public gallery. JPEG, PNG, or HEIC, up to 8 MB.
        </p>
        <div className="mt-4 flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Optional caption (max 280 characters)"
            maxLength={280}
            className="input-field flex-1"
            data-testid="photo-caption-input"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="btn-primary"
            data-testid="photo-upload-button"
          >
            <Upload size={14} strokeWidth={1.5} /> {uploading ? "Uploading..." : "Choose photo"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
            onChange={handleFile}
            className="hidden"
            data-testid="photo-file-input"
          />
        </div>
      </div>

      {myPending.length > 0 && (
        <div data-testid="my-pending-photos">
          <p className="label">Your uploads under review</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-3">
            {myPending.map((p) => (
              <div key={p.id} className="relative group">
                <div className="aspect-square bg-[#E5E1D8] rounded overflow-hidden">
                  <img src={p.thumb_url || p.image_url} alt={p.caption || ""} className="w-full h-full object-cover" />
                </div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <StatusChip status={p.status} />
                  <button
                    onClick={() => removeMyPhoto(p)}
                    className="text-[10px] text-[#B86A5C] hover:underline inline-flex items-center gap-1"
                    data-testid={`my-photo-delete-${p.id}`}
                  >
                    <Trash2 size={10} strokeWidth={1.5} /> Remove
                  </button>
                </div>
                {p.status === "rejected" && p.rejection_reason && (
                  <p className="text-[10px] text-[#B86A5C] mt-1">{p.rejection_reason}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="label">Gallery</p>
        {photos.length === 0 ? (
          <div className="card p-10 mt-3 text-center">
            <ImageOff size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
            <p className="font-serif text-lg mt-3">No photos yet.</p>
            <p className="text-sm text-[#5C6B6B] mt-1">Be the first to share one.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-3" data-testid="hub-photo-grid">
            {photos.map((p) => (
              <a
                key={p.id}
                href={p.image_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block group"
                data-testid={`hub-photo-${p.id}`}
              >
                <div className="aspect-square bg-[#E5E1D8] rounded overflow-hidden">
                  <img src={p.thumb_url || p.image_url} alt={p.caption || ""} className="w-full h-full object-cover transition group-hover:scale-[1.02]" />
                </div>
                {p.caption && <p className="text-xs text-[#5C6B6B] mt-1 line-clamp-2">{p.caption}</p>}
                <p className="text-[10px] text-[#5C6B6B] mt-0.5">— {p.uploader_name}</p>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
