import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, XCircle, ImageOff } from "lucide-react";

function PhotoCard({ photo, onApprove, onReject }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  return (
    <div className="card overflow-hidden flex flex-col" data-testid={`mod-photo-${photo.id}`}>
      <a href={photo.image_url} target="_blank" rel="noopener noreferrer" className="block">
        <div className="aspect-square bg-[#E5E1D8] overflow-hidden">
          <img src={photo.thumb_url || photo.image_url} alt={photo.caption || ""} className="w-full h-full object-cover" />
        </div>
      </a>
      <div className="p-4 flex-1 flex flex-col">
        <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">{photo.workshop_title}</p>
        <p className="text-xs text-[#5C6B6B] mt-1">
          {photo.uploader_name} <span className="text-[#1A2424]/40">·</span> {new Date(photo.created_at).toLocaleDateString()}
        </p>
        {photo.caption && <p className="text-sm mt-2 line-clamp-3">{photo.caption}</p>}

        <div className="mt-auto pt-4">
          {rejecting ? (
            <div className="space-y-2" data-testid={`mod-reject-form-${photo.id}`}>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason (visible to uploader)"
                className="input-field text-xs"
                maxLength={280}
                data-testid={`mod-reject-reason-${photo.id}`}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => { onReject(photo, reason); setRejecting(false); setReason(""); }}
                  className="btn-outline text-xs flex-1 border-[#B86A5C] text-[#B86A5C]"
                  data-testid={`mod-reject-confirm-${photo.id}`}
                >
                  Confirm reject
                </button>
                <button onClick={() => { setRejecting(false); setReason(""); }} className="btn-outline text-xs">Cancel</button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => onApprove(photo)}
                className="btn-primary flex-1 justify-center text-xs"
                data-testid={`mod-approve-${photo.id}`}
              >
                <CheckCircle2 size={13} strokeWidth={1.5} /> Approve
              </button>
              <button
                onClick={() => setRejecting(true)}
                className="btn-outline border-[#B86A5C] text-[#B86A5C] text-xs"
                data-testid={`mod-reject-${photo.id}`}
              >
                <XCircle size={13} strokeWidth={1.5} /> Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PhotoModeration() {
  const { user } = useAuth();
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get("/workshop-photos")
      .then((r) => setPhotos(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const approve = async (p) => {
    try {
      await api.post(`/workshop-photos/${p.id}/approve`);
      toast.success("Photo approved");
      setPhotos((prev) => prev.filter((x) => x.id !== p.id));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Approval failed");
    }
  };
  const reject = async (p, reason) => {
    try {
      await api.post(`/workshop-photos/${p.id}/reject`, { reason });
      toast.success("Photo rejected");
      setPhotos((prev) => prev.filter((x) => x.id !== p.id));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Rejection failed");
    }
  };

  const backTarget = user?.role === "admin" ? "/admin" : "/facilitator";

  return (
    <div className="container-page py-12" data-testid="photo-moderation-page">
      <Link to={backTarget} className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back
      </Link>
      <span className="label">Moderation</span>
      <h1 className="editorial-h1 mt-2">Photo queue</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B]">
        {user?.role === "admin"
          ? "All pending uploads across all workshops."
          : "Pending uploads for the workshops you facilitate."}
      </p>

      {loading ? (
        <div className="py-20 text-center text-sm text-[#5C6B6B]">Loading queue...</div>
      ) : photos.length === 0 ? (
        <div className="card p-16 text-center mt-8">
          <ImageOff size={28} strokeWidth={1.25} className="mx-auto text-[#C9A961]" />
          <p className="font-serif text-lg mt-3">Inbox zero.</p>
          <p className="text-sm text-[#5C6B6B] mt-1">No photos awaiting review.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mt-8" data-testid="mod-photo-grid">
          {photos.map((p) => (
            <PhotoCard key={p.id} photo={p} onApprove={approve} onReject={reject} />
          ))}
        </div>
      )}
    </div>
  );
}
