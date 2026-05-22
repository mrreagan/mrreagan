import React from "react";
import ContactInfo from "../components/ContactInfo";
import ContactForm from "../components/ContactForm";

export default function Contact() {
  return (
    <div className="container-page py-20" data-testid="contact-page">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        <ContactInfo />
        <ContactForm />
      </div>
    </div>
  );
}
