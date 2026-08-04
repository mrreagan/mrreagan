import React from "react";
import { useAuth } from "../contexts/AuthContext";
import { Eye } from "lucide-react";

/**
 * ReadOnlyBanner
 *
 * A slim persistent banner that appears at the top of every page whenever
 * the signed-in user has the `readonly_admin` role. Reinforces to the user
 * (typically outside legal counsel) that no data can be mutated from their
 * session — the backend middleware also enforces this on every request.
 */
export default function ReadOnlyBanner() {
  const { user } = useAuth();
  if (!user || user.role !== "readonly_admin") return null;
  return (
    <div
      className="w-full bg-[#0F2424] text-[#FBF3E4] text-xs text-center py-1.5 px-4"
      data-testid="readonly-admin-banner"
    >
      <span className="inline-flex items-center gap-2">
        <Eye size={12} strokeWidth={1.8} className="text-[#C9A961]" />
        <strong className="uppercase tracking-widest">Counsel review · read-only</strong>
        <span className="text-[#E5D7B3]">
          You have view-only access to every admin and public surface. Any attempt to modify data will be rejected.
        </span>
      </span>
    </div>
  );
}
