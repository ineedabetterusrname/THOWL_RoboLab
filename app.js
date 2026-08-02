/* ============================================================
   TH OWL Robo Lab — Site behavior
   Renders Projects, Templates, Hardware, Safety; handles search.
   ============================================================ */

(function () {
  const data = window.RoboLabData || {};
  const page = document.body.dataset.page;

  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[c]);

  // Build a GitHub URL for a path inside the repo.
  // If `file` is provided, link to that file (blob view); otherwise the folder (tree view).
  const ghUrl = (path, file) => {
    const repo = (data.repo || "").replace(/\/+$/, "");
    const branch = data.branch || "main";
    const clean = String(path || "").replace(/^\/+|\/+$/g, "");
    const kind = file ? "blob" : "tree";
    const tail = file ? `${clean}/${file}` : clean;
    return `${repo}/${kind}/${branch}/${tail}`;
  };

  /* ----------------------- DOWNLOADS ------------------------ */
  // Each entry has a prebuilt archive in downloads/, made by
  // tools/make_downloads.py. Sizes come from the manifest that script writes;
  // if it is missing the links still work, they just carry no size label.
  const zipUrl = (id) => `downloads/${encodeURIComponent(id)}.zip`;

  function labelDownloads(manifest) {
    Object.keys(manifest).forEach((id) => {
      const link = document.getElementById(`download-${id}`);
      const bytes = manifest[id] && manifest[id].bytes;
      if (!link || !bytes) return;
      const mb = bytes / (1024 * 1024);
      const size = mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
      link.textContent = `Download ZIP (${size})`;
      link.title = `${manifest[id].files} files`;
    });
  }

  function loadDownloadSizes() {
    if (!window.fetch) return;
    fetch("downloads/manifest.json", { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => m && labelDownloads(m))
      .catch(() => {});   // opened over file://, or archives not built yet
  }

  /* ----------------------- TEMPLATES (projects page) -------- */
  function renderTemplates(host) {
    if (!host || !data.templates) return;
    host.innerHTML = data.templates
      .map(
        (t) => `
        <article class="card">
          <span class="tag ${esc(t.tagClass || "")}">${esc(t.tag)}</span>
          <h3>${esc(t.title)}</h3>
          <p>${esc(t.summary)}</p>
          <p class="meta">Stack · ${(t.stack || []).map(esc).join(" / ")}</p>
          <div class="card-foot">
            <span class="mono muted">${esc(t.path)}</span>
            <span class="card-links">
              <a id="download-${esc(t.id)}" class="dl" href="${esc(zipUrl(t.id))}" download>Download ZIP</a>
              <a id="template-gh-${esc(t.id)}" href="${esc(ghUrl(t.path))}" target="_blank" rel="noopener">Open on GitHub</a>
            </span>
          </div>
        </article>`
      )
      .join("");
  }

  /* ----------------------- PROJECTS (projects page) --------- */
  function renderProjects(host) {
    if (!host || !data.projects) return;
    host.innerHTML = data.projects
      .map(
        (p, i) => `
        <article class="feature ${i % 2 === 1 ? "reverse" : ""}" id="${esc(p.id)}">
          <div class="feature-visual">
            <header>
              <span>PROJECT // ${esc(p.number)}</span>
              <span>${esc(p.tag)}</span>
            </header>
            <div class="big-id">${esc(p.title.toUpperCase())}</div>
            <div class="ticks">
              ${(p.ticks || []).map((t) => `<span>${esc(t)}</span>`).join("")}
            </div>
          </div>
          <div class="feature-copy">
            <span class="tag ${esc(p.tagClass || "")}">${esc(p.tag)}</span>
            <h3>${esc(p.subtitle)}</h3>
            <p>${esc(p.summary)}</p>
            <p class="meta">Tools · ${(p.tools || []).map(esc).join(" · ")}</p>
            <ul class="bullets">
              ${(p.controls || []).map((c) => `<li>${esc(c)}</li>`).join("")}
            </ul>
            <div class="card-foot">
              <span class="mono muted">${esc(p.path)}</span>
              <span class="card-links">
                <a id="download-${esc(p.id)}" class="dl" href="${esc(zipUrl(p.id))}" download>Download ZIP</a>
                <a id="project-gh-${esc(p.id)}" href="${esc(ghUrl(p.path, p.file))}" target="_blank" rel="noopener">${p.file ? "Open " + esc(p.file) + " on GitHub" : "Open on GitHub"}</a>
              </span>
            </div>
          </div>
        </article>`
      )
      .join("");
  }

  /* ----------------------- ROADMAP (home page) -------------- */
  // The homepage roadmap used to be hand-written HTML and drifted out of
  // sync whenever a project was added to data.js. Both pages now render
  // from the same data.
  function renderRoadmap(host) {
    if (!host || !data.projects) return;
    const brief = (s) => {
      const i = String(s).indexOf(". ");
      return i > 0 ? s.slice(0, i + 1) : s;
    };
    const items = [
      ...(data.templates || []).map((t) => ({
        ...t, line: brief(t.summary), href: "projects.html#templates", cta: "Templates",
      })),
      ...(data.projects || []).map((p) => ({
        ...p, line: `${p.subtitle}. ${brief(p.summary)}`, href: `projects.html#${p.id}`, cta: "Open project",
      })),
    ];
    host.innerHTML = items
      .map(
        (it) => `
        <article class="card">
          <span class="tag ${esc(it.tagClass || "")}">${esc(it.tag)}</span>
          <h3>${esc(it.title)}</h3>
          <p>${esc(it.line)}</p>
          <div class="card-foot">
            <span class="mono muted">${esc(it.path)}</span>
            <a id="roadmap-${esc(it.id)}" href="${esc(it.href)}">${esc(it.cta)}</a>
          </div>
        </article>`
      )
      .join("");
  }

  /* ----------------------- SAFETY (hardware page) ----------- */
  function renderSafety(host) {
    if (!host || !data.safety) return;
    host.innerHTML = data.safety
      .map(
        (s) => `
        <div class="callout ${esc(s.level)}">
          <div class="ico">${esc(s.icon)}</div>
          <div>
            <strong>${esc(s.title)}</strong>
            <span>${esc(s.body)}</span>
          </div>
        </div>`
      )
      .join("");
  }

  /* ----------------------- HARDWARE (hardware page) --------- */
  function renderHardware(host, query, category) {
    if (!host || !data.hardware) return;
    const q = (query || "").toLowerCase().trim();
    const cat = category || "All";

    const items = data.hardware.filter((h) => {
      const catOk = cat === "All" || h.category === cat;
      if (!catOk) return false;
      if (!q) return true;
      const hay =
        (h.name + " " + h.category + " " + h.summary + " " +
          Object.entries(h.specs || {}).map(([k, v]) => `${k} ${v}`).join(" "))
          .toLowerCase();
      return hay.includes(q);
    });

    if (!items.length) {
      host.innerHTML = `<p class="muted">No hardware matches your filter.</p>`;
      return;
    }

    host.innerHTML = items
      .map(
        (h) => `
        <article class="hw-card">
          <div class="hw-head">
            <span class="hw-cat">${esc(h.category)}</span>
          </div>
          <h3>${esc(h.name)}</h3>
          <p>${esc(h.summary)}</p>
          <dl class="specs">
            ${Object.entries(h.specs || {})
              .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`)
              .join("")}
          </dl>
        </article>`
      )
      .join("");
  }

  function buildHardwareFilters(host, getActive, setActive) {
    if (!host || !data.hardware) return;
    const cats = ["All", ...Array.from(new Set(data.hardware.map((h) => h.category)))];
    host.innerHTML = cats
      .map(
        (c) =>
          `<button id="filter-cat-${esc(c.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase())}" class="chip ${c === getActive() ? "active" : ""}" data-cat="${esc(c)}">${esc(c)}</button>`
      )
      .join("");
    host.querySelectorAll(".chip").forEach((btn) =>
      btn.addEventListener("click", () => {
        setActive(btn.dataset.cat);
        host.querySelectorAll(".chip").forEach((c) =>
          c.classList.toggle("active", c.dataset.cat === getActive())
        );
      })
    );
  }

  /* ----------------------- CONTACT (contact page) ----------- */
  function renderContactPeople(host) {
    if (!host || !data.contact || !data.contact.people) return;
    host.innerHTML = data.contact.people
      .map(
        (p) => `
        <article class="card">
          <span class="tag tag-navy">CAAD</span>
          <h3>${esc(p.name)}</h3>
          <p>${esc(p.role)}</p>
          <div class="card-foot">
            <span class="mono muted">E-Mail</span>
            <a id="contact-mail-${esc(p.id)}" href="mailto:${esc(p.email)}">${esc(p.email)}</a>
          </div>
        </article>`
      )
      .join("");
  }

  const val = (id) => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  };

  const DAY_MS = 86400000;
  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

  // "2026-05-05" -> "05.05.2026"
  function formatDate(iso) {
    const parts = String(iso).split("-");
    return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : iso;
  }

  // Inclusive span, rounded up to whole weeks — the label asks for weeks.
  function spanInDays(fromIso, untilIso) {
    const from = new Date(`${fromIso}T00:00:00`);
    const until = new Date(`${untilIso}T00:00:00`);
    if (isNaN(from.getTime()) || isNaN(until.getTime())) return 0;
    return Math.round((until - from) / DAY_MS) + 1;
  }

  function checkedWeekdays() {
    const host = document.getElementById("req-weekdays");
    if (!host) return [];
    return Array.prototype.slice
      .call(host.querySelectorAll("input[type=checkbox]"))
      .filter((c) => c.checked)
      .map((c) => c.value);
  }

  function timeWindowText() {
    const from = val("req-date-from");
    const until = val("req-date-until");
    if (!from || !until) return "";
    const days = spanInDays(from, until);
    const weeks = Math.max(1, Math.ceil(days / 7));
    return `${formatDate(from)} – ${formatDate(until)} (${plural(weeks, "week")}, ${plural(days, "day")})`;
  }

  function routineText() {
    const days = checkedWeekdays().join(", ");
    const from = val("req-time-from");
    const until = val("req-time-until");
    const hours = from && until ? `${from} – ${until}` : "";
    return [days, hours].filter(Boolean).join(" · ");
  }

  // The six request lines, in the order they appear in the sent message.
  // `block` fields put their value on its own line under the label.
  const REQUEST_FIELDS = [
    { id: "req-title", label: "Project Title" },
    { id: "req-prof", label: "Responsible Person (Prof.)" },
    { id: "req-description", label: "Project Short description", block: true },
    { id: "req-person", label: "Person in charge of works on the robot" },
    { label: "Time Window of use (weeks)", value: timeWindowText },
    { label: "Routine week/hours of time of use", value: routineText },
  ];

  function requestBody() {
    const lines = [];
    REQUEST_FIELDS.forEach((f) => {
      const value = f.value ? f.value() : val(f.id);
      if (f.block) {
        lines.push("", `${f.label}:`, value, "");
      } else {
        lines.push(`${f.label}: ${value}`);
      }
    });
    return lines.join("\r\n");
  }

  // Cross-field rules the browser can't express on its own. Setting custom
  // validity here means the native bubble blocks submit, so the submit
  // handler only ever runs on a coherent date/time range.
  function syncValidity() {
    const dFrom = val("req-date-from");
    const dUntil = document.getElementById("req-date-until");
    if (dUntil) {
      dUntil.setCustomValidity(
        dFrom && dUntil.value && dUntil.value < dFrom
          ? "The end date must be on or after the start date."
          : ""
      );
    }

    const tFrom = val("req-time-from");
    const tUntil = document.getElementById("req-time-until");
    if (tUntil) {
      tUntil.setCustomValidity(
        tFrom && tUntil.value && tUntil.value <= tFrom
          ? "The end time must be later than the start time."
          : ""
      );
    }

    const host = document.getElementById("req-weekdays");
    if (host) {
      const boxes = Array.prototype.slice.call(host.querySelectorAll("input[type=checkbox]"));
      if (boxes.length) {
        const any = boxes.some((c) => c.checked);
        boxes[0].setCustomValidity(any ? "" : "Select at least one weekday.");
      }
    }

    const hint = document.getElementById("req-weeks-hint");
    if (hint) {
      const from = val("req-date-from");
      const until = val("req-date-until");
      if (from && until && until >= from) {
        const days = spanInDays(from, until);
        const weeks = Math.max(1, Math.ceil(days / 7));
        hint.textContent = `${plural(weeks, "week")} · ${plural(days, "day")} requested.`;
      } else {
        hint.textContent = "Pick a start and an end date — the number of weeks is worked out for you.";
      }
    }
  }

  function wireRequestForm(form) {
    if (!form || !data.contact) return;

    const status = document.getElementById("request-status");
    const say = (msg, ok) => {
      if (!status) return;
      status.textContent = msg;
      status.classList.toggle("ok", !!ok);
    };

    form.addEventListener("input", syncValidity);
    form.addEventListener("change", syncValidity);
    syncValidity();

    // Native validation runs first — submit only fires once every field is valid.
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const subject =
        `${data.contact.subjectPrefix || "Robot Lab Request"} — ` + val("req-title");

      window.location.href =
        `mailto:${data.contact.to}` +
        `?cc=${encodeURIComponent(data.contact.cc || "")}` +
        `&subject=${encodeURIComponent(subject)}` +
        `&body=${encodeURIComponent(requestBody())}`;

      say("Your e-mail program should now be open with the request ready — check it, then press send.", true);
    });

    const copyBtn = document.getElementById("btn-copy-request");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        const manual = `Couldn't copy automatically — select the text and copy it manually, then mail it to ${data.contact.to}.`;
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
          say(manual);
          return;
        }
        navigator.clipboard.writeText(requestBody()).then(
          () => say(`Request copied. Paste it into an e-mail to ${data.contact.to}, with ${data.contact.cc} in copy.`, true),
          () => say(manual)
        );
      });
    }
  }

  /* ----------------------- WIRING --------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    if (page === "home") {
      renderRoadmap(document.getElementById("roadmap-grid"));
    }

    if (page === "projects") {
      renderTemplates(document.getElementById("templates-grid"));
      renderProjects(document.getElementById("projects-list"));
      loadDownloadSizes();   // after the cards exist, so the links are there to label
    }

    if (page === "hardware") {
      renderSafety(document.getElementById("safety-list"));

      const grid = document.getElementById("hardware-grid");
      const search = document.getElementById("hw-search");
      const filters = document.getElementById("hw-filters");

      let activeCat = "All";
      let query = "";

      const refresh = () => renderHardware(grid, query, activeCat);

      buildHardwareFilters(
        filters,
        () => activeCat,
        (c) => {
          activeCat = c;
          refresh();
        }
      );

      if (search) {
        search.addEventListener("input", (e) => {
          query = e.target.value;
          refresh();
        });
      }

      refresh();
    }

    if (page === "contact") {
      renderContactPeople(document.getElementById("contact-people"));
      wireRequestForm(document.getElementById("robot-request-form"));
    }
  });
})();
