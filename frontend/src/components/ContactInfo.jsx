import React from "react";
import { Mail, MapPin, Phone } from "lucide-react";

export default function ContactInfo() {
  return (
    <div className="lg:col-span-5">
      <span className="label">Contact</span>
      <h1 className="editorial-h1 mt-3">We'd love to hear from you.</h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] leading-relaxed">
        For workshop inquiries, sponsorship questions, facilitator interest, or anything else — write us. We answer within two business days.
      </p>
      <div className="mt-10 space-y-5">
        <InfoRow icon={MapPin} label="Visit us">
          2148 W Earll Dr
          <br />
          Phoenix, AZ 85015
        </InfoRow>
        <InfoRow icon={Mail} label="Email">
          <a href="mailto:hello@birthright.live" className="hover:text-[#476B6B]">
            hello@birthright.live
          </a>
        </InfoRow>
        <InfoRow icon={Phone} label="Phone">
          (602) 330-2650
        </InfoRow>
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start gap-4">
      <Icon size={18} strokeWidth={1.5} className="text-[#C9A961] mt-1 shrink-0" />
      <div>
        <p className="text-xs label text-[#C9A961]">{label}</p>
        <div className="text-sm text-[#1A2424] mt-1">{children}</div>
      </div>
    </div>
  );
}
