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
            <a id="template-gh-${esc(t.id)}" href="${esc(ghUrl(t.path))}" target="_blank" rel="noopener">Open on GitHub</a>
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
        <article class="feature ${i % 2 === 1 ? "reverse" : ""}">
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
              <a id="project-gh-${esc(p.id)}" href="${esc(ghUrl(p.path, p.file))}" target="_blank" rel="noopener">${p.file ? "Open " + esc(p.file) + " on GitHub" : "Open on GitHub"}</a>
            </div>
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

  /* ----------------------- WIRING --------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    if (page === "projects") {
      renderTemplates(document.getElementById("templates-grid"));
      renderProjects(document.getElementById("projects-list"));
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
  });
})();
