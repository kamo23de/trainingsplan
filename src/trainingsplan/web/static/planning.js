// Planungsseite: Events, Verfügbarkeit, Prognose und Kalender.
(function () {
  "use strict";

  const TP = window.TP;
  const { css, esc } = TP;
  const nf0 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });
  const nf1 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 });
  const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
  const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
    "September", "Oktober", "November", "Dezember"];
  const CATEGORY_SLOT = { "Rad": 1, "eBike": 2, "Sonstige": 3 };
  // Intensität geplanter Einheiten: eine Farbe, hell → dunkel
  const INTENSITY = { recovery: 0, openers: 1, endurance: 1, long: 2, tempo: 3, sweetspot: 4, threshold: 5, vo2: 6 };
  const RAMP = ["#b7d3f6", "#9ec5f4", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"];

  const state = { month: null, plan: null, events: [], today: null };
  let workoutIndex = {};

  // --- Hilfen ------------------------------------------------------------------
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const parse = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const fmtDate = (s) => parse(s).toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" });
  const fmtShort = (s) => parse(s).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
  function fmtH(h) {
    const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
    return hh ? `${hh}:${String(mm).padStart(2, "0")} h` : `${mm} min`;
  }
  async function api(url, opts = {}) {
    const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...opts });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const body = await res.json(); msg = typeof body.detail === "string" ? body.detail : msg; } catch { /* leer */ }
      throw new Error(msg);
    }
    return res.status === 204 ? null : res.json();
  }

  // --- Ausgangslage ------------------------------------------------------------
  function renderStatus() {
    const { plan, events } = state;
    const c = plan.context;
    const main = events.filter((e) => e.priority === "A" && e.end_date >= c.today);
    const next = main[0];
    const daysTo = next ? Math.round((parse(next.start_date) - parse(c.today)) / 86400000) : null;
    const week = plan.weeks[0];
    const tile = (v, u, l, key) => `<div class="tile">${key ? TP.infoButton(key) : ""}<div class="value">${v}<span class="unit">${u}</span></div><div class="label">${l}</div></div>`;
    document.getElementById("plan-status").innerHTML = [
      tile(nf0.format(c.ctl), "", "Fitness (CTL) heute", "ctl"),
      tile((c.tsb > 0 ? "+" : "") + nf0.format(c.tsb), "", "Form (TSB) heute", "tsb"),
      tile(c.ftp ?? "–", c.ftp ? "W" : "", "FTP (aktuell)", "ftp_chart"),
      tile(next ? nf0.format(daysTo) : "–", next ? "Tage" : "", next ? `bis ${esc(next.title)}` : "kein Hauptevent"),
      tile(week ? esc(week.phase) : "–", "", "Phase diese Woche", "phases"),
      tile(week ? fmtH(week.planned_hours) : "–", "", week ? `geplant diese Woche · ${nf0.format(week.planned_tss)} TSS` : "geplant diese Woche"),
    ].join("");
    const msg = document.getElementById("plan-message");
    msg.hidden = !plan.message;
    msg.textContent = plan.message || "";
  }

  // --- Events ------------------------------------------------------------------
  function renderEvents() {
    const today = state.plan.context.today;
    const upcoming = state.events.filter((e) => e.end_date >= today);
    const past = state.events.filter((e) => e.end_date < today);
    const item = (e) => `<li class="event-item ${e.priority === "A" ? "main" : "side"}">
        <button class="event-open" data-edit-event="${e.id}">
          <span class="badge ${e.priority === "A" ? "badge-main" : "badge-side"}">${e.priority === "A" ? "Haupt" : "Neben"}</span>
          <span class="event-title">${esc(e.title)}</span>
          <span class="event-meta">${fmtDate(e.start_date)}${e.days > 1 ? ` – ${fmtShort(e.end_date)} (${e.days} Tage)` : ""}${e.distance_km ? ` · ${nf0.format(e.distance_km)} km` : ""}${e.elevation_m ? ` · ${nf0.format(e.elevation_m)} hm` : ""}</span>
        </button>
      </li>`;
    const mainCount = upcoming.filter((e) => e.priority === "A").length;
    document.querySelector('[data-new-event="A"]').disabled = mainCount >= 3;
    document.querySelector('[data-new-event="A"]').title = mainCount >= 3 ? "Höchstens drei Hauptevents" : "";
    document.getElementById("event-list").innerHTML =
      (upcoming.length ? `<ul class="event-list">${upcoming.map(item).join("")}</ul>` : `<p class="muted">Noch keine Events angelegt.</p>`) +
      (past.length ? `<details class="past-events"><summary>Vergangene Events (${past.length})</summary><ul class="event-list">${past.map(item).join("")}</ul></details>` : "");
  }

  const eventDialog = document.getElementById("event-dialog");
  const eventForm = document.getElementById("event-form");
  function openEventForm(event, defaults = {}) {
    eventForm.reset();
    document.getElementById("event-error").hidden = true;
    const e = event || { priority: "B", days: 1, ...defaults };
    for (const [k, v] of Object.entries(e)) {
      if (eventForm.elements[k]) eventForm.elements[k].value = v ?? "";
    }
    eventForm.elements.id.value = event ? event.id : "";
    document.getElementById("event-dialog-title").textContent = event ? "Event bearbeiten" : (e.priority === "A" ? "Neues Hauptevent" : "Neues Nebenevent");
    document.getElementById("event-delete").hidden = !event;
    eventDialog.showModal();
    eventForm.elements.title.focus();
  }

  eventForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = eventForm.elements;
    const num = (v) => (v === "" ? null : Number(v));
    const body = {
      title: f.title.value, start_date: f.start_date.value, days: Number(f.days.value) || 1,
      priority: f.priority.value, distance_km: num(f.distance_km.value),
      elevation_m: num(f.elevation_m.value), notes: f.notes.value || null,
    };
    try {
      if (f.id.value) await api(`/api/events/${f.id.value}`, { method: "PUT", body: JSON.stringify(body) });
      else await api("/api/events", { method: "POST", body: JSON.stringify(body) });
      eventDialog.close();
      await reload();
    } catch (err) {
      const box = document.getElementById("event-error");
      box.textContent = err.message;
      box.hidden = false;
    }
  });
  document.getElementById("event-delete").addEventListener("click", async () => {
    const id = eventForm.elements.id.value;
    const title = eventForm.elements.title.value;
    if (!id || !confirm(`„${title}“ wirklich löschen? Der Plan wird danach neu berechnet.`)) return;
    await api(`/api/events/${id}`, { method: "DELETE" });
    eventDialog.close();
    await reload();
  });

  // --- Verfügbarkeit -----------------------------------------------------------
  async function renderAvailability() {
    const data = await api("/api/availability");
    const form = document.getElementById("availability-form");
    form.innerHTML = data.days.map((d) => `<label><span>${d.label}</span>
      <input type="number" name="d${d.weekday}" min="0" max="16" step="0.25" value="${d.hours}"></label>`).join("") +
      `<button type="submit" class="btn primary">Übernehmen</button><span class="saved muted" hidden>gespeichert</span>`;
  }
  document.getElementById("availability-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const form = ev.target;
    const hours = [0, 1, 2, 3, 4, 5, 6].map((i) => Number(form.elements[`d${i}`].value) || 0);
    await api("/api/availability", { method: "PUT", body: JSON.stringify({ hours }) });
    await reload();
    const saved = document.querySelector("#availability-form .saved");
    saved.hidden = false;
    setTimeout(() => { saved.hidden = true; }, 2000);
  });

  // --- Prognose ----------------------------------------------------------------
  let charts = {};
  async function renderProjection() {
    const past = await api("/api/dashboard?range=3m");
    const proj = state.plan.projection;
    const days = [...past.fitness.days.filter((d) => d < state.plan.start), ...proj.map((p) => p.day)];
    const pastLen = days.length - proj.length;
    const pad = (arr, before) => before ? [...arr, ...Array(proj.length).fill(null)] : [...Array(pastLen).fill(null), ...arr];
    const lastPast = (arr) => arr[pastLen - 1];
    const ctlPast = pad(past.fitness.ctl.slice(0, pastLen), true);
    const atlPast = pad(past.fitness.atl.slice(0, pastLen), true);
    const tsbPast = pad(past.fitness.tsb.slice(0, pastLen), true);
    // Prognose schließt an den letzten Ist-Wert an
    const ctlProj = pad(proj.map((p) => p.ctl), false); ctlProj[pastLen - 1] = lastPast(ctlPast);
    const atlProj = pad(proj.map((p) => p.atl), false); atlProj[pastLen - 1] = lastPast(atlPast);
    const tsbProj = pad(proj.map((p) => p.tsb), false); tsbProj[pastLen - 1] = lastPast(tsbPast);

    const today = state.plan.context.today;
    const evMarks = state.events.filter((e) => e.start_date >= days[0] && e.start_date <= days[days.length - 1])
      .map((e) => ({ xAxis: e.start_date, label: { formatter: e.title, color: css("--text-secondary"), fontSize: 11 },
        lineStyle: { color: e.priority === "A" ? css("--series-7") : css("--text-muted"), type: e.priority === "A" ? "solid" : "dotted", width: e.priority === "A" ? 2 : 1 } }));
    const base = (top) => ({
      animation: false,
      grid: { left: 8, right: 16, top, bottom: 4, containLabel: true },
      tooltip: { trigger: "axis", backgroundColor: css("--surface-1"), borderColor: css("--border"),
        textStyle: { color: css("--text-primary"), fontSize: 12 },
        formatter: (items) => `${fmtDate(items[0].axisValue)}<br>` + items.filter((i) => i.value != null)
          .map((i) => `${i.marker}${i.seriesName}: <b>${nf1.format(i.value)}</b>`).join("<br>") },
      xAxis: { type: "category", data: days, boundaryGap: false, axisTick: { show: false },
        axisLine: { lineStyle: { color: css("--grid") } },
        axisLabel: { color: css("--text-secondary"), formatter: (v) => fmtShort(v) } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: css("--grid") } }, axisLabel: { color: css("--text-secondary") } },
    });
    const line = (name, data, color, dashed, extra = {}) => ({
      name, type: "line", data, showSymbol: false, connectNulls: false,
      lineStyle: { width: 2, color, type: dashed ? "dashed" : "solid" }, itemStyle: { color }, ...extra });

    const o = base(30);
    // Skala an der Fitness ausrichten; Spitzen der Ermüdung während eines
    // mehrtägigen Events werden abgeschnitten, sonst wäre der Rest kaum lesbar
    const maxCtl = Math.max(...[...ctlPast, ...ctlProj].filter((v) => v != null), 50);
    o.yAxis.max = Math.ceil((maxCtl * 1.5) / 20) * 20;
    o.legend = { top: 0, left: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: css("--text-secondary") },
      data: ["Fitness (CTL)", "Ermüdung (ATL)"] };
    o.series = [
      line("Fitness (CTL)", ctlPast, css("--series-1"), false, {
        markLine: { silent: true, symbol: "none", data: [{ xAxis: today, label: { formatter: "heute", color: css("--text-secondary") },
          lineStyle: { color: css("--text-muted"), type: "solid", width: 1 } }, ...evMarks] } }),
      line("Ermüdung (ATL)", atlPast, css("--series-2"), false),
      line("Fitness (CTL)", ctlProj, css("--series-1"), true),
      line("Ermüdung (ATL)", atlProj, css("--series-2"), true, { lineStyle: { width: 1.5, color: css("--series-2"), type: "dashed", opacity: 0.7 } }),
    ];
    charts.main = charts.main || echarts.init(document.getElementById("chart-projection"), null, { renderer: "svg" });
    charts.main.setOption(o, true);

    const p = base(8);
    p.yAxis.min = (v) => Math.max(v.min, -60);
    p.series = [
      line("Form (TSB)", tsbPast, css("--series-3"), false, { areaStyle: { color: css("--series-3"), opacity: 0.12 },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: css("--text-muted"), type: "solid", width: 1 }, data: [{ yAxis: 0 }] } }),
      line("Form (TSB)", tsbProj, css("--series-3"), true),
    ];
    charts.form = charts.form || echarts.init(document.getElementById("chart-projection-form"), null, { renderer: "svg" });
    charts.form.setOption(p, true);
    echarts.connect([charts.main, charts.form]);
  }

  // --- Kalender ----------------------------------------------------------------
  async function renderCalendar() {
    const first = new Date(state.month.getFullYear(), state.month.getMonth(), 1);
    const last = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 0);
    const start = addDays(first, -((first.getDay() + 6) % 7));
    const end = addDays(last, 6 - ((last.getDay() + 6) % 7));
    document.getElementById("cal-month").textContent = `${MONTHS[first.getMonth()]} ${first.getFullYear()}`;
    const data = await api(`/api/calendar?start=${iso(start)}&end=${iso(end)}`);
    const today = data.context.today;

    workoutIndex = {};
    let html = `<div class="cal-head">Woche</div>` + WEEKDAYS.map((d) => `<div class="cal-head">${d}</div>`).join("");
    for (let w = new Date(start); w <= end; w = addDays(w, 7)) {
      const weekKey = iso(w);
      const week = data.weeks[weekKey];
      let actualH = 0, actualTss = 0;
      const cells = [];
      for (let i = 0; i < 7; i++) {
        const key = iso(addDays(w, i));
        const day = data.days[key];
        const inMonth = parse(key).getMonth() === first.getMonth();
        const isPast = key < today;
        day.activities.forEach((a) => { actualH += a.hours; actualTss += a.tss || 0; });
        const events = day.events.map((e) => `<button class="cal-item ev ${e.main ? "ev-main" : "ev-side"}" data-edit-event="${e.id}"
            title="${esc(e.title)} – bearbeiten">${e.main ? "★ " : ""}${esc(e.title)}${e.days > 1 ? ` (${e.day_index}/${e.days})` : ""}${e.distance_km ? `<span class="ci-meta">${nf0.format(e.distance_km / e.days)} km</span>` : ""}</button>`).join("");
        const acts = day.activities.map((a) => `<div class="cal-item done" data-activity="${a.id}" tabindex="0" role="button"
            title="${esc(a.name || a.category)} – Details anzeigen"><i class="dot" style="background:${css("--series-" + CATEGORY_SLOT[a.category])}"></i>
            <span class="ci-title">${esc(a.name || a.category)}</span><span class="ci-meta">${fmtH(a.hours)} · ${nf0.format(a.km)} km${a.tss != null ? ` · ${a.tss}${a.load_basis === "hr" ? "*" : ""} TSS` : ""}</span></div>`).join("");
        // Geplante Einheiten gibt es nur ab Planbeginn (heute bzw. morgen)
        const plans = day.workouts.map((p, idx) => {
          const ref = `${key}#${idx}`;
          workoutIndex[ref] = { ...p, day: key };
          return `<button class="cal-item plan" data-workout="${ref}" style="--intensity:${RAMP[INTENSITY[p.kind] ?? 1]}">
            <span class="ci-title">${esc(p.title)}</span><span class="ci-meta">${fmtH(p.hours)} · ${p.tss} TSS</span></button>`;
        }).join("");
        const empty = !events && !acts && !plans && !isPast ? `<button class="cal-add" data-new-event-date="${key}" title="Nebenevent an diesem Tag anlegen">+</button>` : "";
        cells.push(`<div class="cal-day${inMonth ? "" : " other"}${key === today ? " today" : ""}${isPast ? " past" : ""}">
          <div class="cal-date">${parse(key).getDate()}</div>${events}${acts}${plans}${empty}</div>`);
      }
      const sum = [];
      if (week) sum.push(`<span class="phase phase-${week.phase.toLowerCase()}">${esc(week.phase)}</span>`,
        `<span>Plan ${fmtH(week.planned_hours)}</span><span>${nf0.format(week.planned_tss)} TSS</span>`);
      if (actualH > 0) sum.push(`<span class="muted">Ist ${fmtH(actualH)}</span><span class="muted">${nf0.format(actualTss)} TSS</span>`);
      html += `<div class="cal-week">${sum.join("")}</div>${cells.join("")}`;
    }
    document.getElementById("calendar").innerHTML = html;
  }

  // Geplante Einheit im Overlay
  const workoutDialog = document.getElementById("workout-dialog");
  function openWorkout(w) {
    document.getElementById("workout-title").textContent = `${w.title} · ${fmtDate(w.day)}`;
    document.getElementById("workout-body").innerHTML = `
      <div class="tiles act-tiles">
        <div class="tile"><div class="value">${fmtH(w.hours)}</div><div class="label">Dauer</div></div>
        <div class="tile"><div class="value">${w.tss}</div><div class="label">geplante Belastung (TSS)</div></div>
      </div>
      <p>${esc(w.description)}</p>
      <p class="muted">Der Plan wird bei jeder neuen Aktivität und jeder Änderung an Events oder Verfügbarkeit neu berechnet.</p>`;
    workoutDialog.showModal();
  }

  // --- Ereignisse --------------------------------------------------------------
  document.addEventListener("click", (e) => {
    const newEv = e.target.closest("[data-new-event]");
    if (newEv) return openEventForm(null, { priority: newEv.dataset.newEvent });
    const newDate = e.target.closest("[data-new-event-date]");
    if (newDate) return openEventForm(null, { priority: "B", start_date: newDate.dataset.newEventDate });
    const edit = e.target.closest("[data-edit-event]");
    if (edit) return openEventForm(state.events.find((x) => String(x.id) === edit.dataset.editEvent));
    const wo = e.target.closest("[data-workout]");
    if (wo) return openWorkout(workoutIndex[wo.dataset.workout]);
    if (e.target.closest("[data-close]")) { e.target.closest("dialog").close(); return; }
    if (e.target === eventDialog) eventDialog.close();
    if (e.target === workoutDialog) workoutDialog.close();
  });
  document.getElementById("cal-prev").addEventListener("click", () => { state.month.setMonth(state.month.getMonth() - 1); renderCalendar(); });
  document.getElementById("cal-next").addEventListener("click", () => { state.month.setMonth(state.month.getMonth() + 1); renderCalendar(); });
  document.getElementById("cal-today").addEventListener("click", () => { state.month = parse(state.today); state.month.setDate(1); renderCalendar(); });
  window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));

  async function reload() {
    [state.plan, state.events] = await Promise.all([api("/api/plan"), api("/api/events")]);
    state.today = state.plan.context.today;
    if (!state.month) { state.month = parse(state.today); state.month.setDate(1); }
    renderStatus();
    renderEvents();
    await Promise.all([renderCalendar(), renderProjection()]);
  }

  renderAvailability();
  reload();
})();
