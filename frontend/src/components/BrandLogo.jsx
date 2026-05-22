import React from "react";

const LOGO_URL = "https://customer-assets.emergentagent.com/job_c61b4345-eef4-4783-a5af-85e8af10eaf3/artifacts/s0oix25k_image.png";

export function BrandLogo({ size = "md", showMotto = false, className = "" }) {
  const sizes = {
    sm: { img: "h-9 w-9", text: "text-xl", motto: "text-[9px]" },
    md: { img: "h-11 w-11", text: "text-2xl", motto: "text-[10px]" },
    lg: { img: "h-20 w-20", text: "text-4xl", motto: "text-xs" },
  };
  const s = sizes[size];
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img src={LOGO_URL} alt="birthright logo" className={`${s.img} object-contain`} />
      <div className="flex flex-col leading-none">
        <span className={`font-serif ${s.text} text-[#1A2424] tracking-tight`}>birthright</span>
        {showMotto && (
          <span className={`label ${s.motto} mt-1`}>SECURE BONDS &gt; THRIVE</span>
        )}
      </div>
    </div>
  );
}

export default BrandLogo;
