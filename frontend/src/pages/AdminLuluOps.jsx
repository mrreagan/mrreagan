import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Server, Webhook, CheckCircle2, XCircle, RefreshCw, Trash2, Send, AlertTriangle, ShieldCheck } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export default function AdminLuluOps() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [presets, setPresets] = useState([]);
  const [presetEnv, setPresetEnv] = useState("");
  const [validating, setValidating] = useState(false);
  const [hooks, setHooks] = useState(null);
  const [hookEnv, setHookEnv] = useState("");
  const [expectedUrl, setExpectedUrl] = useState("");
  const [loadingHooks, setLoadingHooks] = useState(false);
  const [subscribing, setSubscribing] = useState(false);
  const [actingId, setActingId] = useState(null);

  useEffect(() => {
    if (!user || user.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    refreshHooks();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const refreshHooks = async () => {
    setLoadingHooks(true);
    try {
      const r = await api.get("/lulu/webhooks");
      setHooks(r.data.subscriptions || []);
      setHookEnv(r.data.env);
      setExpectedUrl(r.data.expected_url);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't load webhooks");
      setHooks([]);
    } finally {
      setLoadingHooks(false);
    }
  };

  const runValidation = async () => {
    setValidating(true);
    setPresets([]);
    try {
      const r = await api.post("/lulu/validate-presets");
      setPresets(r.data.results || []);
      setPresetEnv(r.data.env);
      const okCount = (r.data.results || []).filter((p) => p.ok).length;
      const total = (r.data.results || []).length;
      if (okCount === total) toast.success(`All ${total} presets valid in ${r.data.env}.`);
      else toast.warning(`${okCount}/${total} presets valid in ${r.data.env}.`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Validation call failed");
    } finally {
      setValidating(false);
    }
  };

  const subscribe = async () => {
    setSubscribing(true);
    try {
      await api.post("/lulu/webhooks");
      toast.success("Webhook subscribed");
      refreshHooks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Subscribe failed");
    } finally {
      setSubscribing(false);
    }
  };

  const deleteHook = async (id) => {
    if (!window.confirm("Delete this webhook subscription?")) return;
    setActingId(id);
    try {
      await api.delete(`/lulu/webhooks/${id}`);
      toast.success("Deleted");
      refreshHooks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    } finally {
      setActingId(null);
    }
  };

  const sendTest = async (id) => {
    setActingId(id);
    try {
      await api.post(`/lulu/webhooks/${id}/test`);
      toast.success("Test payload sent — check backend logs");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Test failed");
    } finally {
      setActingId(null);
    }
  };

  const isProd = (hookEnv || presetEnv) === "production";
  const ourHook = (hooks || []).find((h) => (h.url || "").startsWith(expectedUrl));

  return (
    <div className="container-page py-12" data-testid="admin-lulu-ops-page">
      <span className="label">Admin · Lulu Operations</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Server size={26} strokeWidth={1.2} /> Lulu cutover console
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Use this page before flipping <code className="text-[#476B6B]">LULU_ENV=production</code>:
        confirm every preset's <code className="text-[#476B6B]">pod_package_id</code> resolves on
        the live account, then subscribe our webhook so order status + tracking
        flow back automatically.
      </p>

      {/* Env banner */}
      <div
        className={`rounded-xl border-2 p-4 mt-6 inline-flex items-center gap-3 ${
          isProd
            ? "border-[#01784E] bg-[#E8F4EC]"
            : "border-[#C9A961] bg-[#FFF8E1]"
        }`}
        data-testid="lulu-env-banner"
      >
        {isProd ? (
          <ShieldCheck size={20} className="text-[#01784E]" strokeWidth={1.5} />
        ) : (
          <AlertTriangle size={20} className="text-[#8B7128]" strokeWidth={1.5} />
        )}
        <div>
          <p className="font-serif text-lg leading-tight">
            Current environment: <span className="uppercase">{hookEnv || presetEnv || "loading…"}</span>
          </p>
          <p className="text-xs text-[#5C6B6B] mt-0.5">
            {isProd
              ? "Live orders are being charged real money. Be sure."
              : "Sandbox — print jobs are simulated. Set LULU_ENV=production in backend/.env to go live."}
          </p>
        </div>
      </div>

      {/* Preset validator */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="lulu-preset-validator">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-serif text-xl inline-flex items-center gap-2">
            <CheckCircle2 size={18} strokeWidth={1.5} className="text-[#476B6B]" />
            Validate POD presets
          </h2>
          <button onClick={runValidation} disabled={validating} className="btn-outline text-sm inline-flex items-center gap-2" data-testid="lulu-validate-btn">
            <RefreshCw size={14} strokeWidth={1.6} className={validating ? "animate-spin" : ""} />
            {validating ? "Validating…" : "Run validation"}
          </button>
        </div>
        <p className="text-xs text-[#5C6B6B] mt-2">
          Hits Lulu's <code className="text-[#476B6B]">/print-job-cost-calculations/</code> for every
          preset. Anything that fails here will fail at checkout — fix before going live.
        </p>
        {presets.length > 0 && (
          <div className="mt-4 space-y-2" data-testid="lulu-validate-results">
            {presets.map((p) => (
              <div key={p.key} className={`rounded-lg border p-3 text-sm ${p.ok ? "border-[#01784E] bg-[#E8F4EC]" : "border-[#9E3C3C] bg-[#FBEAEA]"}`} data-testid={`lulu-preset-row-${p.key}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium inline-flex items-center gap-2">
                    {p.ok ? (
                      <CheckCircle2 size={14} className="text-[#01784E]" strokeWidth={1.8} />
                    ) : (
                      <XCircle size={14} className="text-[#9E3C3C]" strokeWidth={1.8} />
                    )}
                    {p.label}
                  </span>
                  {p.ok ? (
                    <span className="text-xs text-[#5C6B6B]">
                      base ${p.base_cost_usd?.toFixed(2)} · suggested ${p.suggested_retail_usd?.toFixed(2)}
                    </span>
                  ) : (
                    <span className="text-xs text-[#9E3C3C]">FAIL</span>
                  )}
                </div>
                <p className="text-[10px] text-[#5C6B6B] mt-1 font-mono">{p.pod_package_id} · {p.page_count} pages</p>
                {p.error && <p className="text-xs text-[#9E3C3C] mt-1">{p.error}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Webhook subscriptions */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="lulu-webhooks-section">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-serif text-xl inline-flex items-center gap-2">
            <Webhook size={18} strokeWidth={1.5} className="text-[#476B6B]" />
            Lulu → birthright webhooks
          </h2>
          <button onClick={refreshHooks} disabled={loadingHooks} className="btn-outline text-sm inline-flex items-center gap-2" data-testid="lulu-webhooks-refresh">
            <RefreshCw size={14} strokeWidth={1.6} className={loadingHooks ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
        <p className="text-xs text-[#5C6B6B] mt-2">
          On a successful subscription, Lulu fires <code className="text-[#476B6B]">PRINT_JOB_STATUS_CHANGED</code>
          {" "}at our receiver every time a print job transitions. Status + tracking
          flow to the user's Order history automatically.
        </p>
        {expectedUrl && (
          <p className="text-[11px] text-[#5C6B6B] mt-2 font-mono break-all" data-testid="lulu-webhook-expected-url">
            Expected URL: {expectedUrl}
          </p>
        )}

        {!ourHook && hooks !== null && (
          <button onClick={subscribe} disabled={subscribing} className="btn-primary text-sm mt-4 inline-flex items-center gap-2" data-testid="lulu-webhook-subscribe-btn">
            <Webhook size={14} strokeWidth={1.8} />
            {subscribing ? "Subscribing…" : "Subscribe webhook"}
          </button>
        )}

        {hooks && hooks.length > 0 && (
          <div className="mt-4 space-y-2" data-testid="lulu-webhooks-list">
            {hooks.map((h) => {
              const mine = (h.url || "").startsWith(expectedUrl);
              return (
                <div key={h.id} className={`rounded-lg border p-3 text-sm ${mine ? "border-[#476B6B] bg-[#F4F1EA]" : "border-[#E5E1D8] bg-white"}`} data-testid={`lulu-webhook-row-${h.id}`}>
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                      <p className="text-xs font-mono break-all leading-relaxed">{h.url}</p>
                      <p className="text-[10px] text-[#5C6B6B] mt-1">
                        {mine && <span className="text-[#01784E] mr-2 uppercase tracking-wider">· this app</span>}
                        topics: {(h.topics || []).join(", ") || "(none)"} · active: {h.is_active ? "yes" : "no"}
                      </p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button onClick={() => sendTest(h.id)} disabled={actingId === h.id} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`lulu-webhook-test-${h.id}`}>
                        <Send size={11} strokeWidth={1.8} /> Test
                      </button>
                      <button onClick={() => deleteHook(h.id)} disabled={actingId === h.id} className="btn-outline !text-[#9E3C3C] !border-[#9E3C3C] text-xs inline-flex items-center gap-1" data-testid={`lulu-webhook-delete-${h.id}`}>
                        <Trash2 size={11} strokeWidth={1.8} /> Delete
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {hooks && hooks.length === 0 && (
          <p className="text-sm text-[#5C6B6B] mt-3" data-testid="lulu-webhooks-empty">
            No subscriptions yet. Click "Subscribe webhook" above to register this app.
          </p>
        )}
      </section>

      {/* Cutover checklist */}
      <section className="card p-6 mt-6 max-w-3xl bg-[#FAF8F5]" data-testid="lulu-cutover-checklist">
        <h2 className="font-serif text-xl">Cutover checklist</h2>
        <ol className="mt-3 text-sm text-[#5C6B6B] space-y-2 list-decimal list-inside leading-relaxed">
          <li>While in sandbox: run preset validation. All rows must show base costs.</li>
          <li>Set <code className="text-[#476B6B]">LULU_ENV=production</code> in <code className="text-[#476B6B]">backend/.env</code> and run <code className="text-[#476B6B]">sudo supervisorctl restart backend</code>.</li>
          <li>Re-run preset validation here. All rows should still show base costs — production prices may differ from sandbox.</li>
          <li>Click "Subscribe webhook" to register this app's URL with the production Lulu account.</li>
          <li>Click "Test" on the new subscription. Backend logs should show <code className="text-[#476B6B]">lulu webhook: no order matched</code> (expected — Lulu's dummy id won't match any real order).</li>
          <li>Place a small real test order on the live site to confirm end-to-end.</li>
        </ol>
      </section>
    </div>
  );
}
