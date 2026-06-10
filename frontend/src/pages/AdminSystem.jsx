/* eslint-disable */
/**
 * AdminSystem — operator console for system-wide settings + data
 * migrations. Two panels:
 *
 *  1. SUPPORT EMAILS — admin-editable addresses surfaced across the site
 *     (help center, footer, escalation, etc). Lets operators change which
 *     mailbox is shown publicly without a code deploy.
 *
 *  2. DATA MIGRATIONS — one-click runner for any pending data migrations.
 *     Backend auto-runs these on every startup, so this is a belt-and-
 *     suspenders manual control. Live audit of what's been applied
 *     against the local DB.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Mail, Database, Play, RefreshCw, CheckCircle, Circle } from "lucide-react";
import api from "../lib/api";

export default function AdminSystem() {
  return (
    <div className="container-page py-10 sm:py-14" data-testid="admin-system">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin home
      </Link>
      <h1 className="font-serif text-3xl">System</h1>
      <p className="text-sm text-[#5C6B6B] mt-1 max-w-2xl">
        Operator controls for site-wide configuration and data layer health.
      </p>

      <div className="mt-10 grid lg:grid-cols-2 gap-8">
        <SupportEmailsCard />
        <MigrationsCard />
      </div>
    </div>
  );
}


function SupportEmailsCard() {
  const [settings, setSettings] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ support_email: "", hello_email: "" });

  const load = async () => {
    try {
      const r = await api.get("/admin/system/settings");
      setSettings(r.data);
      setForm({
        support_email: r.data.support_email || "",
        hello_email: r.data.hello_email || "",
      });
    } catch (e) {
      toast.error("Couldn't load settings");
    }
  };
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e?.preventDefault?.();
    setBusy(true);
    try {
      await api.put("/admin/system/settings", form);
      toast.success("Saved");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed");
    } finally { setBusy(false); }
  };

  return (
    <section className="card p-6" data-testid="system-emails-card">
      <header className="flex items-center gap-2 mb-1">
        <Mail size={16} strokeWidth={1.6} className="text-[#A87A4A]" />
        <h2 className="font-serif text-xl">Support email addresses</h2>
      </header>
      <p className="text-xs text-[#5C6B6B] mb-5 leading-relaxed">
        These are the addresses shown on the public site (Help assistant, escalation,
        contact pages). Make sure your DNS / email routing is actually configured to
        receive mail at these addresses — this field only sets what we display.
      </p>
      <form onSubmit={save} className="space-y-4">
        <label className="block">
          <span className="label text-[#476B6B]">Support email (member support, escalation)</span>
          <input
            type="email" required
            className="input-field mt-1"
            value={form.support_email}
            onChange={(e) => setForm({ ...form, support_email: e.target.value })}
            data-testid="system-support-email"
          />
        </label>
        <label className="block">
          <span className="label text-[#476B6B]">Hello email (general inquiries, press)</span>
          <input
            type="email" required
            className="input-field mt-1"
            value={form.hello_email}
            onChange={(e) => setForm({ ...form, hello_email: e.target.value })}
            data-testid="system-hello-email"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="btn-primary text-sm"
          data-testid="system-emails-save"
        >
          {busy ? "Saving…" : "Save"}
        </button>
      </form>
      {settings?.updated_at && (
        <p className="text-[10px] text-[#9DA8A8] mt-3">
          Last updated {new Date(settings.updated_at).toLocaleString()} by {settings.updated_by}
        </p>
      )}
    </section>
  );
}


function MigrationsCard() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = await api.get("/admin/system/migrations");
      setData(r.data);
    } catch {
      toast.error("Couldn't load migrations");
    }
  };
  useEffect(() => { load(); }, []);

  const run = async (force = false) => {
    setBusy(true);
    try {
      const r = await api.post("/admin/system/run-migrations", { force });
      const applied = r.data.log.filter((x) => x.status === "applied").length;
      const errors = r.data.log.filter((x) => x.status === "error");
      if (errors.length) {
        toast.error(`Stopped at error: ${errors[0].id}`);
      } else if (applied === 0) {
        toast.message("Nothing to apply — already up to date.");
      } else {
        toast.success(`Applied ${applied} migration${applied === 1 ? "" : "s"}`);
      }
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Migration run failed");
    } finally { setBusy(false); }
  };

  return (
    <section className="card p-6" data-testid="system-migrations-card">
      <header className="flex items-center gap-2 mb-1">
        <Database size={16} strokeWidth={1.6} className="text-[#476B6B]" />
        <h2 className="font-serif text-xl">Data migrations</h2>
      </header>
      <p className="text-xs text-[#5C6B6B] mb-5 leading-relaxed">
        These run automatically on backend startup. The list below shows what's
        been applied to THIS environment's database. If you see any rows that
        say "PENDING," click <em>Run pending now</em> and the database will
        catch up. Re-running already-applied migrations is safe.
      </p>

      {data === null && <p className="text-sm italic text-[#5C6B6B]">Loading…</p>}
      {data && (
        <>
          <ul className="space-y-2 mb-5" data-testid="migrations-list">
            {data.migrations.map((m) => (
              <li
                key={m.id}
                className="flex items-start gap-2 text-sm"
                data-testid={`migration-row-${m.id}`}
              >
                {m.applied ? (
                  <CheckCircle size={14} strokeWidth={1.7} className="text-[#2E5C46] mt-0.5 shrink-0" />
                ) : (
                  <Circle size={14} strokeWidth={1.7} className="text-[#C9A961] mt-0.5 shrink-0" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-[12px]">{m.id}</p>
                  {m.applied && m.applied_at && (
                    <p className="text-[10px] text-[#9DA8A8]">
                      applied {new Date(m.applied_at).toLocaleString()}
                    </p>
                  )}
                  {!m.applied && (
                    <p className="text-[10px] text-[#A87A4A] uppercase tracking-wider">PENDING</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => run(false)}
              disabled={busy}
              className="btn-primary text-xs inline-flex items-center gap-1.5"
              data-testid="run-migrations-btn"
            >
              <Play size={11} strokeWidth={2} />
              {busy ? "Running…" : `Run pending (${data.pending_count})`}
            </button>
            <button
              onClick={load}
              disabled={busy}
              className="text-xs text-[#476B6B] hover:text-[#1A2424] inline-flex items-center gap-1"
            >
              <RefreshCw size={11} strokeWidth={1.7} /> Refresh
            </button>
            <button
              onClick={() => run(true)}
              disabled={busy}
              className="text-xs text-[#A87A4A] hover:text-[#1A2424] ml-auto"
              title="Re-run every migration regardless of applied state (idempotent)"
              data-testid="force-migrations-btn"
            >
              Force re-run all
            </button>
          </div>
        </>
      )}
    </section>
  );
}
