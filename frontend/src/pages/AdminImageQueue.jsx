/**
 * AdminImageQueue — review additional product images before publish.
 *
 * Flow:
 *   1. Admin clicks "Scan products" → backend audits each product's
 *      description vs current AI vision caption and queues a focused
 *      prompt for every product that mentions a detail the hero shot
 *      doesn't show.
 *   2. Each row is a `pending_additional_images` entry. Admin clicks
 *      Generate (calls Nano Banana ~15-25s), then Publish or Discard.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, RefreshCcw, Sparkles, Check, Trash2, ImagePlus } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

const STATUS_PILLS = {
  queued:     "bg-[#FBF1DC] text-[#7C5316]",
  generating: "bg-[#FFF7DC] text-[#7C5316] animate-pulse",
  ready:      "bg-[#E8F0E8] text-[#2F5D32]",
  published:  "bg-[#E6EEF4] text-[#1F3942]",
  failed:     "bg-[#F4DCDC] text-[#7C1F1F]",
};

export default function AdminImageQueue() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [busyIds, setBusyIds] = useState(new Set());

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/products/image-queue");
      setItems(r.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const markBusy = (id, on) => {
    setBusyIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(id); else next.delete(id);
      return next;
    });
  };

  const runScan = async () => {
    setScanning(true);
    try {
      const r = await api.post("/admin/products/image-queue/scan");
      const { scanned, queued, skipped, errors } = r.data;
      toast.success(`Scanned ${scanned} · queued ${queued} · skipped ${skipped}${errors ? ` · ${errors} errors` : ""}`);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Scan failed");
    } finally {
      setScanning(false);
    }
  };

  const generate = async (id) => {
    markBusy(id, true);
    try {
      const r = await api.post(`/admin/products/image-queue/${id}/generate`);
      setItems((prev) => prev.map((it) => (it.id === id ? r.data : it)));
      toast.success("Image generated");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Generation failed");
      await load();
    } finally {
      markBusy(id, false);
    }
  };

  const publish = async (id) => {
    markBusy(id, true);
    try {
      await api.post(`/admin/products/image-queue/${id}/publish`);
      toast.success("Published to product");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Publish failed");
    } finally {
      markBusy(id, false);
    }
  };

  const discard = async (id) => {
    markBusy(id, true);
    try {
      await api.post(`/admin/products/image-queue/${id}/discard`);
      setItems((prev) => prev.filter((it) => it.id !== id));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Discard failed");
    } finally {
      markBusy(id, false);
    }
  };

  const pending = items.filter((i) => i.status !== "published");

  return (
    <div className="container-page py-12" data-testid="admin-image-queue-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>
      <div className="flex items-start justify-between gap-6 flex-wrap mb-8">
        <div>
          <span className="label">Image Studio</span>
          <h1 className="editorial-h1 mt-3">Additional product images</h1>
          <p className="text-sm text-[#5C6B6B] mt-3 max-w-xl">
            We audit each product&apos;s description against its current AI vision caption.
            When a description references a detail the hero photo doesn&apos;t show (a flame
            stamped inside the mug, a label sewn into the inseam) we queue a focused
            prompt for a second shot. You review every generated image before it goes live.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="btn-outline text-sm inline-flex items-center gap-2"
            data-testid="image-queue-refresh"
          >
            <RefreshCcw size={14} strokeWidth={1.5} /> Refresh
          </button>
          <button
            onClick={runScan}
            disabled={scanning}
            className="btn-primary text-sm inline-flex items-center gap-2"
            data-testid="image-queue-scan"
          >
            <Sparkles size={14} strokeWidth={1.5} />
            {scanning ? "Scanning... (1-2 min)" : "Scan products"}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-[#5C6B6B]" data-testid="image-queue-loading">Loading...</p>}

      {!loading && pending.length === 0 && (
        <div className="card p-8 text-center" data-testid="image-queue-empty">
          <ImagePlus size={32} strokeWidth={1.2} className="mx-auto text-[#5C6B6B]" />
          <p className="font-serif text-xl mt-4">No images in the queue.</p>
          <p className="text-sm text-[#5C6B6B] mt-2">
            Run a scan to surface products whose descriptions mention details
            the current photo doesn&apos;t show.
          </p>
        </div>
      )}

      {!loading && pending.length > 0 && (
        <div className="space-y-4" data-testid="image-queue-list">
          {pending.map((entry) => {
            const busy = busyIds.has(entry.id);
            const pill = STATUS_PILLS[entry.status] || STATUS_PILLS.queued;
            return (
              <article
                key={entry.id}
                className="card p-5 grid grid-cols-1 md:grid-cols-[180px_1fr_auto] gap-5 items-start"
                data-testid={`image-queue-entry-${entry.id}`}
              >
                <div className="w-[180px] h-[180px] bg-[#F4F1EA] rounded overflow-hidden">
                  {entry.image_url ? (
                    <img
                      src={entry.image_url}
                      alt={`Generated for ${entry.product_name}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[#5C6B6B] text-xs">
                      Not generated yet
                    </div>
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-serif text-lg">{entry.product_name}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium ${pill}`} data-testid={`image-queue-status-${entry.id}`}>
                      {entry.status}
                    </span>
                  </div>
                  <p className="text-xs text-[#5C6B6B] mt-1">
                    Product ID: {entry.product_id} · Queued {entry.created_at?.slice(0, 16)?.replace("T", " ")}
                  </p>
                  <p className="text-sm text-[#1A2424] mt-3 whitespace-pre-wrap leading-relaxed">
                    {entry.prompt}
                  </p>
                  {entry.error && (
                    <p className="text-xs text-[#7C1F1F] mt-3" data-testid={`image-queue-error-${entry.id}`}>
                      Error: {entry.error}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-2 md:min-w-[160px]">
                  {(entry.status === "queued" || entry.status === "failed") && (
                    <button
                      onClick={() => generate(entry.id)}
                      disabled={busy}
                      className="btn-primary text-sm justify-center"
                      data-testid={`image-queue-generate-${entry.id}`}
                    >
                      <Sparkles size={14} strokeWidth={1.5} />
                      {busy ? "Generating..." : "Generate"}
                    </button>
                  )}
                  {entry.status === "ready" && (
                    <button
                      onClick={() => publish(entry.id)}
                      disabled={busy}
                      className="btn-primary text-sm justify-center"
                      data-testid={`image-queue-publish-${entry.id}`}
                    >
                      <Check size={14} strokeWidth={1.5} /> Publish
                    </button>
                  )}
                  <button
                    onClick={() => discard(entry.id)}
                    disabled={busy}
                    className="btn-outline text-sm justify-center"
                    data-testid={`image-queue-discard-${entry.id}`}
                  >
                    <Trash2 size={14} strokeWidth={1.5} /> Discard
                  </button>
                  <Link
                    to={`/equip/${entry.product_id}`}
                    target="_blank"
                    className="text-xs text-[#476B6B] hover:underline text-center"
                  >
                    View product →
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
