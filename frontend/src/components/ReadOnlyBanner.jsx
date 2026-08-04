import React from "react";
import { useAuth } from "../contexts/AuthContext";
import { Eye } from "lucide-react";

/**
 * ReadOnlyBanner
 *
 * A slim persistent banner that appears at the top of every page whenever
 * the signed-in user has the `readonly_admin` role. Reinforces to counsel
 * that their write privileges are scoped: they can shop, comment, and
 * author legal work, but the general admin surface is fenced off.
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
        <strong className="uppercase tracking-widest">Counsel · scoped access</strong>
        <span className="text-[#E5D7B3]">
          Full read access. You can shop, comment, and upload legal notices. General admin settings are read-only.
        </span>
      </span>
    </div>
  );
}
