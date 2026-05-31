/* Universal "Modeling vs. Committing" indicator.
 *
 * Render inside any route where the visitor is browsing a role/feature
 * WITHOUT having committed to it. Disappears as soon as they enroll.
 * Consistent visual language across every Explore-before-Embrace surface.
 */
import React from "react";
import { Eye } from "lucide-react";

export default function PreviewModeBanner({
  label = "Preview mode",
  message = "You're modeling the experience — nothing is committed until you enroll.",
  variant = "default",
}) {
  const styles = {
    default: { bg: "bg-[#FAF8F5]", border: "border-[#C9A961]", iconColor: "text-[#C9A961]", textColor: "text-[#1A2424]" },
    sandbox: { bg: "bg-[#F4F1EA]", border: "border-[#476B6B]", iconColor: "text-[#476B6B]", textColor: "text-[#1A2424]" },
    invitation: { bg: "bg-[#FAF8F5]", border: "border-[#9E3C3C]", iconColor: "text-[#9E3C3C]", textColor: "text-[#1A2424]" },
  }[variant] || { bg: "bg-[#FAF8F5]", border: "border-[#C9A961]", iconColor: "text-[#C9A961]", textColor: "text-[#1A2424]" };

  return (
    <div
      className={`${styles.bg} border-l-4 ${styles.border} px-4 py-3 flex items-start gap-3 rounded-r-md`}
      data-testid="preview-mode-banner"
    >
      <Eye size={18} className={`${styles.iconColor} mt-0.5 flex-shrink-0`} />
      <div className="flex-1 text-sm leading-relaxed">
        <strong className={styles.textColor}>{label}.</strong>{" "}
        <span className="text-[#5C6B6B]">{message}</span>
      </div>
    </div>
  );
}
