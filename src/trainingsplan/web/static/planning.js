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
  const CATEGORY_SLOT = { "Rad": 1, "eBike": 2, "Sonstige": 3, "Laufen": 4, "Rudern": 5, "Kraft": 6 };
  // Intensität geplanter Einheiten: eine Farbe, hell → dunkel
  const INTENSITY = { recovery: 0, openers: 1, endurance: 1, long: 2, tempo: 3, sweetspot: 4, threshold: 5, vo2: 6, row: 1, run: 1, core: 0 };
  const CROSS = { row: "Rudern", run: "Laufen", core: "Rumpf" };
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

  // --- Ergänzungstraining -----------------------------------------------------
  async function renderOptions() {
    const data = await api("/api/options");
    document.getElementById("options-form").innerHTML = data.options.map((o) =>
      `<label class="toggle"><input type="checkbox" name="${o.key}" ${o.enabled ? "checked" : ""}> ${esc(o.label)}</label>`).join("") +
      `<span class="saved muted" hidden>gespeichert</span>`;
  }
  document.getElementById("options-form").addEventListener("change", async (ev) => {
    const form = ev.currentTarget;
    const options = Object.fromEntries([...form.querySelectorAll("input")].map((i) => [i.name, i.checked]));
    await api("/api/options", { method: "PUT", body: JSON.stringify({ options }) });
    await reload();
    const saved = form.querySelector(".saved");
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
            <span class="ci-title">${TP.scoreBadge(a.compliance, true)}${esc(a.name || a.category)}</span><span class="ci-meta">${fmtH(a.hours)} · ${nf0.format(a.km)} km${a.tss != null ? ` · ${a.tss}${a.load_basis === "hr" ? "*" : ""} TSS` : ""}</span></div>`).join("");
        // Geplante Einheiten gibt es nur ab Planbeginn (heute bzw. morgen)
        const plans = day.workouts.map((p, idx) => {
          const ref = `${key}#${idx}`;
          workoutIndex[ref] = { ...p, day: key };
          const cross = CROSS[p.kind];
          return `<button class="cal-item plan${cross ? " cross" : ""}${p.missed ? " missed" : ""}" data-workout="${ref}" style="--intensity:${RAMP[INTENSITY[p.kind] ?? 1]}">
            <span class="ci-title">${cross ? `<span class="sport">${cross}</span>` : ""}${esc(cross ? p.title.replace(/^(Rudern|Laufen): /, "") : p.title)}</span><span class="ci-meta">${p.missed ? "verpasst · " : ""}${fmtH(p.hours)} · ${p.tss} TSS</span></button>`;
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
  function fmtStep(st, ftp) {
    const dur = st.seconds ? fmtH(st.seconds / 3600) : "bis Rundentaste";
    const target = st.low != null ? ` · ${st.low}–${st.high} % FTP${ftp ? ` (${Math.round(st.low * ftp / 100)}–${Math.round(st.high * ftp / 100)} W)` : ""}` : "";
    return `<li><span class="st-name">${esc(st.name)}</span><span class="st-meta">${dur}${target}${st.notes ? " · " + esc(st.notes) : ""}</span></li>`;
  }
  function renderSteps(steps, ftp) {
    return `<ol class="steps">${steps.map((st) => st.repeat
      ? `<li class="repeat"><span class="st-name">${st.repeat} ×</span><ol>${st.steps.map((x) => fmtStep(x, ftp)).join("")}</ol></li>`
      : fmtStep(st, ftp)).join("")}</ol>`;
  }

  async function openWorkout(w) {
    document.getElementById("workout-title").textContent = `${w.title} · ${fmtDate(w.day)}`;
    const program = w.program && TP.exercises ? TP.exercises.renderProgram(w.program) : "";
    workoutDialog.classList.toggle("wide", Boolean(program));
    const body = document.getElementById("workout-body");
    body.innerHTML = `
      ${w.missed ? `<p class="missed-note">Diese Einheit wurde nicht absolviert.</p>` : ""}
      <div class="tiles act-tiles">
        <div class="tile"><div class="value">${fmtH(w.hours)}</div><div class="label">Dauer</div></div>
        <div class="tile"><div class="value">${w.tss}</div><div class="label">geplante Belastung (TSS)</div></div>
      </div>
      ${program || `<p>${esc(w.description)}</p>`}
      <div id="workout-structure"></div>
      <div class="garmin-box" id="garmin-box"></div>
      <p class="muted">Der Plan wird bei jeder neuen Aktivität und jeder Änderung an Events oder Verfügbarkeit neu berechnet.</p>`;
    workoutDialog.showModal();
    body.scrollTop = 0;
    if (!w.id) return;
    try {
      const [detail, device] = await Promise.all([api(`/api/planned/${w.id}`), api("/api/device")]);
      if (!program && detail.steps.length > 1) {
        document.getElementById("workout-structure").innerHTML = `<h4 class="steps-head">Ablauf auf dem Gerät</h4>${renderSteps(detail.steps, detail.ftp_w)}`;
      }
      if (detail.exportable && !w.missed) renderGarminBox(detail, device);
    } catch (err) {
      document.getElementById("garmin-box").innerHTML = `<p class="form-error">${esc(err.message)}</p>`;
    }
  }

  function renderGarminBox(detail, device) {
    const box = document.getElementById("garmin-box");
    box.innerHTML = `
      <h4>Auf Garmin übertragen ${TP.infoButton("garmin_transfer")}</h4>
      <p class="sub">${device.connected
        ? `Gerät gefunden: <code>${esc(device.path)}</code>`
        : "Kein Garmin-Gerät als Laufwerk gefunden. Gerät per USB anschließen oder die Datei herunterladen."}</p>
      <div class="actions">
        <button class="btn primary" id="garmin-send" ${device.connected ? "" : "disabled"}>Auf Gerät übertragen</button>
        <a class="btn" href="/api/planned/${detail.id}/fit" download="${esc(detail.file_name)}">FIT-Datei herunterladen</a>
        ${device.connected ? "" : `<button class="btn" id="garmin-recheck">Erneut suchen</button>`}
      </div>
      <p class="garmin-status" id="garmin-status" role="status" aria-live="polite"></p>`;
    const status = (t, cls = "") => { const el = document.getElementById("garmin-status"); el.textContent = t; el.className = "garmin-status " + cls; };
    document.getElementById("garmin-recheck")?.addEventListener("click", async () => renderGarminBox(detail, await api("/api/device")));
    document.getElementById("garmin-send")?.addEventListener("click", async (ev) => {
      ev.target.disabled = true;
      status("Wird übertragen …");
      try {
        const r = await api(`/api/planned/${detail.id}/send`, { method: "POST" });
        status(`Übertragen nach ${r.path}. Gerät auswerfen – das Workout erscheint danach unter Training › Workouts.`, "ok");
      } catch (err) {
        status(err.message, "error");
        ev.target.disabled = false;
      }
    });
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
  let resizeTimer;
  window.addEventListener("resize", () => {
    Object.values(charts).forEach((c) => c.resize());
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => state.plan && renderSeason(), 150);
  });


  // --- Saisonübersicht ---------------------------------------------------------
  // Zeitstrahl bis nach dem letzten Hauptevent: Phasen, Entlastungswochen, Events
  // (per Ziehen verschiebbar) und die prognostizierte Fitness.
  const FOCUS = {
    "Grundlage": "Z2-Umfang aufbauen, 1× Tempo pro Woche, Samstag lang",
    "Aufbau": "Sweet Spot und Schwelle, lange Wochenendfahrten",
    "Spezifisch": "eventnah: Back-to-back-Wochenenden, Verpflegung üben",
    "Tapering": "Umfang reduzieren, kurz und knackig",
    "Event": "Vorbelastung, dann los",
    "Regeneration": "locker, viel Ruhe",
  };
  const LABEL_W = 96;
  const ROW = { month: 0, phase: 22, deload: 64, events: 92, ctl: 188 };
  const SEASON_H = 300;
  let season = null; // Geometrie der zuletzt gezeichneten Übersicht

  function renderSeason() {
    const host = document.getElementById("season");
    const weeks = state.plan.weeks;
    if (!weeks.length) { host.innerHTML = `<p class="muted">Lege ein Hauptevent an, dann erscheint hier die Saison.</p>`; host.style.height = "auto"; return; }
    const first = parse(weeks[0].start);
    const days = weeks.length * 7;
    const avail = host.parentElement.clientWidth - LABEL_W - 8;
    const dayW = Math.max(3.4, avail / days);
    const width = LABEL_W + days * dayW;
    const xOf = (iso) => LABEL_W + ((parse(iso) - first) / 86400000) * dayW;
    season = { first, dayW, xOf, days };
    host.style.width = `${width}px`;
    host.style.height = `${SEASON_H}px`;
    const parts = [];

    // Zeilenbeschriftungen
    [["Phase", ROW.phase + 8], ["Entlastung", ROW.deload], ["Events", ROW.events + 14], ["Fitness", ROW.ctl + 30]]
      .forEach(([t, y]) => parts.push(`<div class="s-rowlabel" style="top:${y}px">${t}</div>`));

    // Monate
    for (let m = new Date(first.getFullYear(), first.getMonth() + 1, 1); (m - first) / 86400000 < days; m = new Date(m.getFullYear(), m.getMonth() + 1, 1)) {
      const x = xOf(iso(m));
      parts.push(`<div class="s-month" style="left:${x}px">${MONTHS[m.getMonth()].slice(0, 3)}${m.getMonth() === 0 ? " " + m.getFullYear() : ""}</div>`);
      parts.push(`<div class="s-grid" style="left:${x}px"></div>`);
    }

    // Phasen als durchgehende Bänder (Entlastungswochen gehören zu ihrer Phase)
    let i = 0;
    while (i < weeks.length) {
      let j = i;
      while (j + 1 < weeks.length && weeks[j + 1].base_phase === weeks[i].base_phase) j++;
      const phase = weeks[i].base_phase;
      const x0 = xOf(weeks[i].start), x1 = xOf(weeks[j].start) + 7 * dayW;
      const w = x1 - x0 - 3;
      const focus = FOCUS[phase] || "";
      parts.push(`<button class="s-phase phase-${phase.toLowerCase()}" data-month="${weeks[i].start}" style="left:${x0 + 1}px;width:${w}px"
        title="${esc(phase)} · ${fmtShort(weeks[i].start)}–${fmtShort(iso(addDays(parse(weeks[j].start), 6)))} (${j - i + 1} Wochen)\n${esc(focus)}">
        <b>${w > 70 ? esc(phase) : esc(phase.slice(0, 4)) + "."}</b>${w > 260 ? `<span>${esc(focus)}</span>` : ""}</button>`);
      i = j + 1;
    }

    // Wochen: Entlastung markiert, Tooltip mit Planwerten, Klick springt in den Kalender
    const proj = Object.fromEntries(state.plan.projection.map((p) => [p.day, p]));
    weeks.forEach((w) => {
      const x = xOf(w.start);
      const ctl = proj[w.start] ? ` · CTL ${nf0.format(proj[w.start].ctl)}` : "";
      const tip = `Woche ab ${fmtShort(w.start)} · ${w.phase} · Plan ${fmtH(w.planned_hours)}, ${nf0.format(w.planned_tss)} TSS${ctl}${w.note ? "\n" + w.note : ""}`;
      const cls = w.phase === "Entlastung" ? "s-week deload" : w.note ? "s-week shifted" : "s-week";
      parts.push(`<button class="${cls}" data-month="${w.start}" style="left:${x + 1}px;width:${7 * dayW - 2}px" title="${esc(tip)}">${w.phase === "Entlastung" ? "E" : w.note ? "↷" : ""}</button>`);
    });

    // Events in Spuren, damit sich nahe Termine nicht überdecken
    const lanes = [];
    const evs = state.events.filter((e) => e.end_date >= weeks[0].start && e.start_date <= iso(addDays(first, days)))
      .sort((a, b) => a.start_date.localeCompare(b.start_date));
    evs.forEach((e) => {
      const xs = xOf(e.start_date), xe = xOf(e.end_date) + dayW;
      const w = Math.max(124, xe - xs);
      // kurze Events: Block um das Datum zentrieren, lange: vom Start bis zum Ende
      const left = xe - xs >= 124 ? xs : xs + (xe - xs) / 2 - w / 2;
      let lane = lanes.findIndex((end) => end < left - 4);
      if (lane < 0) { lane = lanes.length; lanes.push(0); }
      lanes[lane] = left + w;
      const top = ROW.events + Math.min(lane, 1) * 44;
      parts.push(`<div class="s-event ${e.priority === "A" ? "main" : "side"}" tabindex="0" role="button"
        data-event="${e.id}" style="left:${left}px;width:${w}px;top:${top}px"
        title="${esc(e.title)} · ${fmtDate(e.start_date)}${e.days > 1 ? ` (${e.days} Tage)` : ""} – ziehen zum Verschieben, Klick zum Bearbeiten">
        <b>${e.priority === "A" ? "★ " : ""}${esc(e.title)}</b><span class="s-date">${fmtShort(e.start_date)}${e.distance_km ? ` · ${nf0.format(e.distance_km)} km` : ""}</span></div>`);
    });

    // Fitness-Prognose als Linie
    const allPts = state.plan.projection;
    if (allPts.length) {
      // Skala bis zum Start des letzten Hauptevents; der Anstieg während eines
      // mehrtägigen Events wird oben abgeschnitten, sonst wäre der Rest flach
      // Linie bis zum Start des letzten Hauptevents: danach sagt die Prognose wenig
      const lastMain = state.events.filter((e) => e.priority === "A").map((e) => e.start_date).sort().pop();
      const pts = allPts.filter((p) => !lastMain || p.day <= lastMain);
      const vals = pts.map((p) => p.ctl);
      const lo = Math.min(...vals) - 5, hi = Math.max(...vals) + 5;
      const H = 90;
      const y = (v) => ROW.ctl + H - ((Math.min(v, hi) - lo) / (hi - lo)) * H;
      const poly = pts.map((p) => `${(xOf(p.day) + dayW / 2).toFixed(1)},${y(p.ctl).toFixed(1)}`).join(" ");
      const marks = [];
      const label = (p, text, anchor) => marks.push(`<div class="s-ctl-label ${anchor}" style="left:${xOf(p.day)}px;top:${y(p.ctl) - 22}px">${text}</div>`);
      label(pts[0], `heute ${nf0.format(pts[0].ctl)}`, "start");
      state.events.filter((e) => e.priority === "A").forEach((e) => {
        const p = pts.find((q) => q.day === e.start_date);
        if (p) label(p, `Start: CTL ${nf0.format(p.ctl)} · Form ${p.tsb > 0 ? "+" : ""}${nf0.format(p.tsb)}`, "end");
      });
      parts.push(`<svg class="s-ctl" width="${width}" height="${SEASON_H}" aria-hidden="true">
        <polyline points="${poly}" fill="none" stroke="${css("--series-1")}" stroke-width="2.5" stroke-linejoin="round"/></svg>`, ...marks);
    }

    // Heute
    parts.push(`<div class="s-today" style="left:${xOf(state.plan.context.today)}px" title="heute"></div>`);
    host.innerHTML = parts.join("");
  }

  // Ziehen, Klicken und Tastatur auf Events in der Übersicht
  const seasonEl = document.getElementById("season");
  const seasonStatus = (t) => { document.getElementById("season-status").textContent = t; };
  let drag = null;

  async function moveEvent(id, deltaDays) {
    const e = state.events.find((x) => String(x.id) === String(id));
    if (!e || !deltaDays) return;
    let start = addDays(parse(e.start_date), deltaDays);
    if (iso(start) < state.today) start = parse(state.today);
    const body = { title: e.title, start_date: iso(start), days: e.days, priority: e.priority,
      distance_km: e.distance_km, elevation_m: e.elevation_m, notes: e.notes };
    seasonStatus(`${e.title} wird auf ${fmtDate(iso(start))} verschoben …`);
    try {
      await api(`/api/events/${e.id}`, { method: "PUT", body: JSON.stringify(body) });
      await reload();
      seasonStatus(`${e.title} liegt jetzt am ${fmtDate(iso(start))}. Der Plan wurde neu berechnet.`);
      const el = seasonEl.querySelector(`[data-event="${e.id}"]`);
      if (el && document.activeElement === document.body) el.focus();
    } catch (err) {
      seasonStatus(`Verschieben nicht möglich: ${err.message}`);
      await reload();
    }
  }

  seasonEl.addEventListener("pointerdown", (ev) => {
    const el = ev.target.closest(".s-event");
    if (!el || ev.button !== 0) return;
    ev.preventDefault();
    el.setPointerCapture(ev.pointerId);
    const e = state.events.find((x) => String(x.id) === el.dataset.event);
    drag = { el, id: el.dataset.event, x0: ev.clientX, days: 0, start: e.start_date, label: el.querySelector(".s-date") };
    el.classList.add("dragging");
  });
  seasonEl.addEventListener("pointermove", (ev) => {
    if (!drag) return;
    let days = Math.round((ev.clientX - drag.x0) / season.dayW);
    const minDays = Math.round((parse(state.today) - parse(drag.start)) / 86400000);
    days = Math.max(days, minDays);
    drag.days = days;
    drag.el.style.transform = `translateX(${days * season.dayW}px)`;
    drag.label.textContent = fmtShort(iso(addDays(parse(drag.start), days))) + (days ? ` (${days > 0 ? "+" : ""}${days} T.)` : "");
  });
  const endDrag = (ev) => {
    if (!drag) return;
    const { el, id, days } = drag;
    drag = null;
    el.classList.remove("dragging");
    if (ev.type === "pointercancel") { renderSeason(); return; }
    if (days === 0) { el.style.transform = ""; openEventForm(state.events.find((x) => String(x.id) === id)); return; }
    moveEvent(id, days);
  };
  seasonEl.addEventListener("pointerup", endDrag);
  seasonEl.addEventListener("pointercancel", endDrag);

  // Tastatur: Pfeile verschieben um einen Tag (mit Umschalt um eine Woche), Enter bearbeitet
  let keyMove = { id: null, days: 0, timer: null };
  seasonEl.addEventListener("keydown", (ev) => {
    const el = ev.target.closest(".s-event");
    if (!el) return;
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); openEventForm(state.events.find((x) => String(x.id) === el.dataset.event)); return; }
    if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
    ev.preventDefault();
    const step = (ev.key === "ArrowLeft" ? -1 : 1) * (ev.shiftKey ? 7 : 1);
    if (keyMove.id !== el.dataset.event) keyMove = { id: el.dataset.event, days: 0, timer: null };
    keyMove.days += step;
    el.style.transform = `translateX(${keyMove.days * season.dayW}px)`;
    const e = state.events.find((x) => String(x.id) === el.dataset.event);
    el.querySelector(".s-date").textContent = fmtShort(iso(addDays(parse(e.start_date), keyMove.days)));
    clearTimeout(keyMove.timer);
    keyMove.timer = setTimeout(() => { const { id, days } = keyMove; keyMove = { id: null, days: 0, timer: null }; moveEvent(id, days); }, 700);
  });

  // Klick auf Phase oder Woche: Kalender auf diesen Monat
  seasonEl.addEventListener("click", (ev) => {
    const target = ev.target.closest("[data-month]");
    if (!target) return;
    state.month = parse(target.dataset.month);
    state.month.setDate(1);
    renderCalendar().then(() => document.getElementById("calendar-section").scrollIntoView({ behavior: "smooth", block: "start" }));
  });

  // Offene Zuordnungen: Aktivitäten, bei denen unklar ist, welche Einheit gemeint war
  async function renderOpenAssignments() {
    const open = await api("/api/compliance/open");
    const box = document.getElementById("assign-banner");
    box.hidden = !open.length;
    if (!open.length) return;
    box.innerHTML = `<h2>Bitte Zuordnung bestätigen ${TP.infoButton("compliance")}</h2>
      <p class="sub">Bei ${open.length === 1 ? "dieser Aktivität" : `diesen ${open.length} Aktivitäten`} ist nicht eindeutig, welche geplante Einheit gemeint war.</p>
      <div class="assign-list">${open.map((o) => `<button class="btn" data-activity="${o.activity_id}">
        ${fmtDate(o.date.slice(0, 10))} · ${esc(o.name || o.category)}${o.compliance.planned_title ? ` <span class="muted">→ ${esc(o.compliance.planned_title)}?</span>` : ""}</button>`).join("")}</div>`;
  }
  document.addEventListener("tp:assignment", () => { renderOpenAssignments(); renderCalendar(); });

  async function reload() {
    [state.plan, state.events] = await Promise.all([api("/api/plan"), api("/api/events")]);
    state.today = state.plan.context.today;
    if (!state.month) { state.month = parse(state.today); state.month.setDate(1); }
    renderStatus();
    renderEvents();
    renderSeason();
    await Promise.all([renderCalendar(), renderProjection(), renderOpenAssignments()]);
  }

  renderAvailability();
  renderOptions();
  reload();
})();
