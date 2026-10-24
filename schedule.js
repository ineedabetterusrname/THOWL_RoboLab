/* ============================================================
   TH OWL Robo Lab — Robot schedule
   Edit this file and push to GitHub to update the calendar on
   the Contact page.

   How a day is resolved (later rules win):
     1. `weekly`     — the regular pattern for each weekday
     2. `exceptions` — date ranges that override the pattern,
                       applied in the order listed
   Days after `validUntil` (and before `validFrom`) show as
   "Ask supervisors".

   status: "available" | "booked" | "requested" | "event" | "unavailable"
   Dates are YYYY-MM-DD. `to` is inclusive and optional.
   ============================================================ */

window.RoboLabSchedule = {
  validFrom: "2026-10-01",
  validUntil: "2026-11-30",

  weekly: {
    mon: { status: "booked",      title: "RESET Conference working session", time: "All day",            who: "Hrithik, Tareef & Hossein" },
    tue: { status: "available",   title: "Available for booking",            time: "11:00 – 17:00" },
    wed: { status: "available",   title: "Available for booking",            time: "14:00 – 17:00" },
    thu: { status: "booked",      title: "RESET Conference working session", time: "After lunch",        who: "Hrithik, Tareef & Hossein" },
    fri: { status: "booked",      title: "Research Project – Robotic Brick Deconstruction", time: "All day", who: "Hossein" },
    sat: { status: "unavailable", title: "Unavailable" },
    sun: { status: "unavailable", title: "Unavailable" },
  },

  exceptions: [
    { from: "2026-10-27", status: "requested", title: "Booking requested", time: "14:00 – 17:00", who: "Soroush" },
    { from: "2026-11-09", to: "2026-11-22", status: "unavailable", title: "Unavailable" },
    { from: "2026-11-17", to: "2026-11-18", status: "event", title: "RESET Conference" },
  ],
};
