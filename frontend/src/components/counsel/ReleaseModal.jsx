/**
 * ReleaseModal — admin confirms the release of a working draft as a new
 * ratification. Version defaults to a minor bump from the latest
 * ratification; admin can override.
 */
import React, { useState } from "react";
import { ShieldCheck, X as XIcon } from "lucide-react";
import { bumpMinor } from "./diffHelpers";

export function ReleaseModal({ data, ratifications, onCancel, onRelease, busy }) {
  const { slug, title, wd } = data;
  const latest = (ratifications || [])
    .filter((r) => r.source_slug === slug)
    .sort((a, b) => (b.ratified_at || "").localeCompare(a.ratified_at || ""))[0];
  const defaultVersion = bumpMinor(latest?.version || "");
  const [version, setVersion] = useState(defaultVersion);
  const [notes, setNotes] = useState(`Released working draft ${wd?.id?.slice(0, 8) || ""}`);
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60] p-4" data-testid="release-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-md w-full p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="label">Release working draft</span>
            <h2 className="font-serif text-2xl mt-1">{title}</h2>
          </div>
          <button onClick={onCancel} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="release-modal-close">
            <XIcon size={18} />
          </button>
        </div>
        <p className="text-xs text-[#5C6B6B] mt-3">
          Promoting the working draft overwrites the released .md, rebuilds the .docx bundle, and creates a new ratification record. The public site will start showing this version immediately.
        </p>
        <div className="mt-4 space-y-3">
          <div>
            <label className="label block mb-1">Version</label>
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="e.g. 1.3"
              className="input input-bordered w-full text-sm"
              data-testid="release-modal-version"
            />
            <p className="text-[10px] text-[#5C6B6B] mt-1">Prior released version: <strong>{latest?.version || "none"}</strong> · default is a minor bump.</p>
          </div>
          <div>
            <label className="label block mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input input-bordered w-full text-sm h-20"
              data-testid="release-modal-notes"
            />
          </div>
        </div>
        <div className="mt-5 flex gap-2 justify-end">
          <button onClick={onCancel} className="btn-outline text-sm" data-testid="release-modal-cancel">Cancel</button>
          <button
            onClick={() => onRelease(version.trim(), notes.trim())}
            disabled={busy || !version.trim()}
            className="btn-primary text-sm inline-flex items-center gap-1 bg-[#1E4030]"
            data-testid="release-modal-confirm"
          >
            <ShieldCheck size={14} /> {busy ? "Releasing…" : `Release v${version || "?"}`}
          </button>
        </div>
      </div>
    </div>
  );
}
