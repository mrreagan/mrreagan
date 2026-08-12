import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Mail, CheckCircle2, XCircle, AlertCircle, ShieldCheck, Send, RefreshCw } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import Explainer from "../components/Explainer";

export default function AdminEmailOps() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [log, setLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [testRecipient, setTestRecipient] = useState("");
  const [sendingTest, setSendingTest] = useState(false);

  useEffect(() => {
    if (!user || user.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    setTestRecipient(user.email || "");
    refresh();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const refresh = async () => {
    setLoading(true);
    try {
      const [s, l] = await Promise.all([
        api.get("/admin/email-status"),
        api.get("/admin/email-log?limit=15"),
      ]);
      setStatus(s.data);
      setLog(l.data.items || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't load email status");
    } finally {
      setLoading(false);
    }
  };

  const sendTest = async () => {
    if (!testRecipient || !testRecipient.includes("@")) {
      toast.error("Enter a valid recipient email");
      return;
    }
    setSendingTest(true);
    try {
      const r = await api.post("/admin/email-test", { to: testRecipient.trim() });
      if (r.data.real_send_enabled) {
        toast.success(`Live email sent to ${testRecipient} (id: ${r.data.email_id || "n/a"})`);
      } else {
        toast.message(`Dry-run queued (id: ${r.data.email_id})`, {
          description: "EMAIL_DRY_RUN is still true. Flip it to send a real email.",
        });
      }
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Test send failed");
    } finally {
      setSendingTest(false);
    }
  };

  const live = status?.real_send_enabled;

  return (
    <div className="container-page py-12" data-testid="admin-email-ops-page">
      <span className="label">Admin · Email Operations</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Mail size={26} strokeWidth={1.2} /> Email cutover console <Explainer id="emailops.page" size={16} />
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Use this page to flip <code className="text-[#476B6B]">EMAIL_DRY_RUN=false</code> safely:
        confirm Resend is configured and DNS is verified, then send a self-test before going live.
      </p>

      {/* Mode banner */}
      <div
        className={`rounded-xl border-2 p-4 mt-6 inline-flex items-center gap-3 ${
          live
            ? "border-[#01784E] bg-[#E8F4EC]"
            : "border-[#C9A961] bg-[#FFF8E1]"
        }`}
        data-testid="email-mode-banner"
      >
        {live ? (
          <ShieldCheck size={20} className="text-[#01784E]" strokeWidth={1.5} />
        ) : (
          <AlertCircle size={20} className="text-[#8B7128]" strokeWidth={1.5} />
        )}
        <div>
          <p className="font-serif text-lg leading-tight">
            Mode: <span className="uppercase">{live ? "live" : "dry-run"}</span>
          </p>
          <p className="text-xs text-[#5C6B6B] mt-0.5">
            {live
              ? "Real emails are flowing through Resend. Mind the send volume."
              : "Outbound emails are queued to MongoDB only. No external delivery."}
          </p>
        </div>
      </div>

      {/* Readiness checklist */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="email-readiness-section">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-serif text-xl">Readiness checklist <Explainer id="emailops.readiness" size={13} /></h2>
          <button onClick={refresh} disabled={loading} className="btn-outline text-sm inline-flex items-center gap-2" data-testid="email-refresh-btn">
            <RefreshCw size={14} strokeWidth={1.6} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
        {status && (
          <div className="mt-4 space-y-2">
            {status.checklist.map((row, i) => {
              const okIcon = row.ok === true
                ? <CheckCircle2 size={14} className="text-[#01784E]" strokeWidth={1.8} />
                : row.ok === false
                ? <XCircle size={14} className="text-[#9E3C3C]" strokeWidth={1.8} />
                : <AlertCircle size={14} className="text-[#8B7128]" strokeWidth={1.8} />;
              const bg = row.ok === true
                ? "border-[#01784E] bg-[#E8F4EC]"
                : row.ok === false
                ? "border-[#9E3C3C] bg-[#FBEAEA]"
                : "border-[#C9A961] bg-[#FFF8E1]";
              return (
                <div key={i} className={`rounded-lg border p-3 text-sm ${bg}`} data-testid={`email-checklist-row-${i}`}>
                  <p className="font-medium inline-flex items-center gap-2">
                    {okIcon}{row.step}
                  </p>
                  <p className="text-[11px] text-[#5C6B6B] mt-1 leading-relaxed">{row.hint}</p>
                </div>
              );
            })}
          </div>
        )}
        {status && (
          <div className="mt-4 text-[11px] text-[#5C6B6B] grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="email-stats">
            <div><span className="block uppercase tracking-wider text-[#476B6B]">Sender</span><span className="font-mono">{status.sender_email}</span></div>
            <div><span className="block uppercase tracking-wider text-[#476B6B]">Reply-to</span><span className="font-mono">{status.reply_to_email}</span></div>
            <div><span className="block uppercase tracking-wider text-[#476B6B]">Sent total</span><span>{status.sent_count} (failed: {status.failed_count})</span></div>
            <div><span className="block uppercase tracking-wider text-[#476B6B]">Dry-run queued</span><span>{status.queued_dry_run_count}</span></div>
          </div>
        )}
      </section>

      {/* Test sender */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="email-test-section">
        <h2 className="font-serif text-xl inline-flex items-center gap-2">
          <Send size={18} strokeWidth={1.5} className="text-[#476B6B]" />
          Send a test email
        </h2>
        <p className="text-xs text-[#5C6B6B] mt-2">
          In dry-run, this just queues an entry in <code className="text-[#476B6B]">db.outbound_emails</code>.
          In live mode, it actually sends via Resend — use after the checklist is green.
        </p>
        <div className="mt-4 flex flex-col sm:flex-row gap-2">
          <input
            type="email"
            value={testRecipient}
            onChange={(e) => setTestRecipient(e.target.value)}
            placeholder="recipient@example.com"
            className="input-field text-sm flex-1"
            data-testid="email-test-recipient"
          />
          <button onClick={sendTest} disabled={sendingTest} className="btn-primary text-sm inline-flex items-center gap-2" data-testid="email-test-send-btn">
            <Send size={14} strokeWidth={1.8} />
            {sendingTest ? "Sending…" : live ? "Send live test" : "Send dry-run test"}
          </button>
        </div>
      </section>

      {/* Recent log */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="email-log-section">
        <h2 className="font-serif text-xl">Most recent emails <Explainer id="emailops.recent" size={13} /></h2>
        {log.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-2">No emails yet.</p>
        ) : (
          <div className="mt-4 space-y-2">
            {log.map((row) => (
              <div key={row.id} className="rounded-lg border border-[#E5E1D8] p-3 text-sm" data-testid={`email-log-row-${row.id}`}>
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-medium">{row.subject}</span>
                  <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${row.status === "sent" ? "bg-[#E8F4EC] text-[#01784E]" : row.status === "failed" ? "bg-[#FBEAEA] text-[#9E3C3C]" : "bg-[#FFF8E1] text-[#8B7128]"}`}>
                    {row.status || "queued"}
                  </span>
                </div>
                <p className="text-[11px] text-[#5C6B6B] mt-1">
                  {row.template} · to {(row.to || []).join(", ")} · {row.created_at?.slice(0, 19)?.replace("T", " ")}
                </p>
                {row.error && <p className="text-[11px] text-[#9E3C3C] mt-1">{row.error}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Cutover checklist */}
      <section className="card p-6 mt-6 max-w-3xl bg-[#FAF8F5]" data-testid="email-cutover-checklist">
        <h2 className="font-serif text-xl">Cutover checklist <Explainer id="emailops.cutover" size={13} /></h2>
        <ol className="mt-3 text-sm text-[#5C6B6B] space-y-2 list-decimal list-inside leading-relaxed">
          <li>Get a Resend API key. Set <code className="text-[#476B6B]">RESEND_API_KEY=re_xxx</code> in <code className="text-[#476B6B]">backend/.env</code>.</li>
          <li>In Resend dashboard, verify the sender domain (add SPF/DKIM/DMARC DNS records). Domain row must show green.</li>
          <li>Confirm <code className="text-[#476B6B]">SENDER_EMAIL</code> uses an address on the verified domain.</li>
          <li>Flip <code className="text-[#476B6B]">EMAIL_DRY_RUN=false</code> in <code className="text-[#476B6B]">backend/.env</code>.</li>
          <li>Run <code className="text-[#476B6B]">sudo supervisorctl restart backend</code>.</li>
          <li>Refresh this page. Mode banner should turn green ("LIVE"). Send a test to yourself above.</li>
          <li>Check the recent log — your test should appear with status <code className="text-[#476B6B]">sent</code>.</li>
        </ol>
      </section>
    </div>
  );
}
