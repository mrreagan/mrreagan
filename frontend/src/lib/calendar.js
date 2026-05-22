/**
 * Generate and download an .ics file for a workshop.
 */
const fmt = (d) => new Date(d).toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

export default function downloadIcs(workshop) {
  const ics = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//birthright//workshop//EN",
    "BEGIN:VEVENT",
    `UID:${workshop.id}@birthright.live`,
    `DTSTAMP:${fmt(new Date())}`,
    `DTSTART:${fmt(workshop.start_date)}`,
    `DTEND:${fmt(workshop.end_date)}`,
    `SUMMARY:${workshop.title}`,
    `DESCRIPTION:${(workshop.short_description || "").replace(/\n/g, " ")}`,
    `LOCATION:${workshop.location_name}, ${workshop.location_address}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\n");
  const blob = new Blob([ics], { type: "text/calendar" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${workshop.slug}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}
