// Dashboard: lädt /api/dashboard und zeichnet Kennzahlen, Diagramme und Tabellen.
(function () {
  "use strict";

  const CATEGORY_SLOT = { "Rad": 1, "eBike": 2, "Sonstige": 3 };
  const nf0 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });
  const nf1 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const charts = {};
  let state = { range: localStorageGet("range") || "1y" };

  function localStorageGet(key) {
    try { return localStorage.getItem("tp." + key); } catch { return null; }
  }
  function localStorageSet(key, value) {
    try { localStorage.setItem("tp." + key, value); } catch { /* ignorieren */ }
  }

  function css(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }
  function series(slot) { return css("--series-" + slot); }

  function fmtDate(iso) {
    const [y, m, d] = iso.slice(0, 10).split("-");
    return `${d}.${m}.${y}`;
  }
  function fmtHours(h) {
    const hh = Math.floor(h);
    const mm = Math.round((h - hh) * 60);
    return `${hh}:${String(mm).padStart(2, "0")} h`;
  }
  function esc(s) {
    return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  // Gemeinsame Diagramm-Grundlage: zurückhaltendes Raster, Tooltip mit Fadenkreuz.
  function base() {
    const text = css("--text-secondary");
    const grid = css("--grid");
    return {
      animation: false,
      textStyle: { fontFamily: getComputedStyle(document.body).fontFamily, color: text },
      grid: { left: 8, right: 16, top: 30, bottom: 4, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "line", lineStyle: { color: css("--text-muted") } },
        backgroundColor: css("--surface-1"),
        borderColor: css("--border"),
        textStyle: { color: css("--text-primary"), fontSize: 12 },
      },
      legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10,
                textStyle: { color: text } },
      xAxis: { axisLine: { lineStyle: { color: grid } }, axisTick: { show: false },
               axisLabel: { color: text } },
      yAxis: { splitLine: { lineStyle: { color: grid } }, axisLabel: { color: text } },
    };
  }

  function chart(id) {
    if (!charts[id]) charts[id] = echarts.init(document.getElementById(id), null, { renderer: "svg" });
    return charts[id];
  }

  function line(name, data, slot, extra = {}) {
    return Object.assign({
      name, type: "line", data, showSymbol: false, symbolSize: 8,
      lineStyle: { width: 2, color: series(slot) }, itemStyle: { color: series(slot) },
      emphasis: { focus: "series" },
    }, extra);
  }

  // ---------------------------------------------------------------------------
  function renderKpis(d) {
    const k = d.kpis;
    const tiles = [
      [nf0.format(k.activities), "", "Aktivitäten", "activities"],
      [nf0.format(k.hours), "h", "Trainingszeit gesamt", "hours"],
      [nf0.format(k.bike_km), "km", "Rad (ohne eBike)", "bike_km"],
      [nf0.format(k.elevation_m), "hm", "Höhenmeter", "elevation"],
      [nf1.format(k.bike_hours_per_week), "h", "Rad pro Woche (Ø)", "bike_per_week"],
      [nf0.format(k.long_rides), "", "Fahrten ab 4 h", "long_rides"],
      [nf0.format(k.longest_ride_km), "km", "Längste Fahrt", "longest"],
    ];
    document.getElementById("kpis").innerHTML = tiles.map(([v, u, l, key]) =>
      `<div class="tile">${infoButton(key)}<div class="value">${v}<span class="unit">${u}</span></div><div class="label">${l}</div></div>`
    ).join("");

    const c = d.current;
    const tsbText = c.tsb == null ? "–" : (c.tsb > 0 ? "+" : "") + nf0.format(c.tsb);
    const today = [
      [c.ctl == null ? "–" : nf0.format(c.ctl), "Fitness (CTL) heute", "ctl"],
      [c.atl == null ? "–" : nf0.format(c.atl), "Ermüdung (ATL) heute", "atl"],
      [tsbText, "Form (TSB) heute", "tsb"],
    ];
    document.getElementById("today").innerHTML = today.map(([v, l, key]) =>
      `<div class="tile">${infoButton(key)}<div class="value">${v}</div><div class="label">${l}</div></div>`
    ).join("");
  }

  function renderFitness(d) {
    const f = d.fitness;
    const o = base();
    o.xAxis = Object.assign(o.xAxis, { type: "category", data: f.days, boundaryGap: false,
      axisLabel: { color: css("--text-secondary"), formatter: (v) => fmtDate(v).slice(3) } });
    o.yAxis = Object.assign(o.yAxis, { type: "value" });
    o.tooltip.valueFormatter = (v) => nf1.format(v);
    o.series = [line("Fitness (CTL)", f.ctl, 1), line("Ermüdung (ATL)", f.atl, 2)];
    chart("chart-fitness").setOption(o, true);

    const p = base();
    p.grid.top = 8;
    p.legend = { show: false };
    p.xAxis = Object.assign(p.xAxis, { type: "category", data: f.days, boundaryGap: false,
      axisLabel: { color: css("--text-secondary"), formatter: (v) => fmtDate(v).slice(3) } });
    p.yAxis = Object.assign(p.yAxis, { type: "value" });
    p.tooltip.valueFormatter = (v) => (v > 0 ? "+" : "") + nf1.format(v);
    p.series = [line("Form (TSB)", f.tsb, 3, {
      areaStyle: { color: series(3), opacity: 0.12 },
      markLine: { silent: true, symbol: "none", label: { show: false },
                  lineStyle: { color: css("--text-muted"), type: "solid", width: 1 },
                  data: [{ yAxis: 0 }] },
    })];
    chart("chart-form").setOption(p, true);
    echarts.connect([chart("chart-fitness"), chart("chart-form")]);
  }

  function renderWeekly(d) {
    const w = d.weekly;
    const o = base();
    o.xAxis = Object.assign(o.xAxis, { type: "category", data: w.weeks,
      axisLabel: { color: css("--text-secondary"), formatter: (v) => fmtDate(v).slice(0, 6) } });
    o.yAxis = Object.assign(o.yAxis, { type: "value" });
    o.tooltip.axisPointer = { type: "shadow" };
    o.tooltip.formatter = (items) => {
      const i = items[0].dataIndex;
      const total = items.reduce((s, it) => s + (it.value || 0), 0);
      const rows = items.filter((it) => it.value > 0).map((it) =>
        `${it.marker}${it.seriesName}: <b>${fmtHours(it.value)}</b>`).join("<br>");
      return `Woche ab ${fmtDate(w.weeks[i])}<br>${rows}<br>Gesamt: <b>${fmtHours(total)}</b>` +
        ` · ${nf0.format(w.km[i])} km · ${nf0.format(w.tss[i])} TSS`;
    };
    const cats = Object.keys(w.hours);
    o.series = cats.map((cat, idx) => ({
      name: cat, type: "bar", stack: "h", data: w.hours[cat], barMaxWidth: 18,
      itemStyle: {
        color: series(CATEGORY_SLOT[cat]),
        borderColor: css("--surface-1"), borderWidth: 1,
        borderRadius: idx === cats.length - 1 ? [3, 3, 0, 0] : 0,
      },
      emphasis: { focus: "series" },
    }));
    chart("chart-weekly").setOption(o, true);
  }

  function renderYears(d) {
    const years = d.years;
    const o = base();
    o.grid.right = 96;
    const months = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
    const monthStarts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335];
    o.xAxis = Object.assign(o.xAxis, { type: "value", min: 1, max: 366, interval: 30.5,
      axisLabel: { color: css("--text-secondary"),
        formatter: (v) => { const i = monthStarts.findIndex((s) => Math.abs(s - v) < 16); return i >= 0 ? months[i] : ""; } },
      splitLine: { show: false } });
    o.yAxis = Object.assign(o.yAxis, { type: "value",
      axisLabel: { color: css("--text-secondary"), formatter: (v) => nf0.format(v) } });
    o.tooltip.formatter = (items) => {
      const day = items[0].value[0];
      const dt = new Date(2001, 0, day);
      return `${dt.getDate()}. ${months[dt.getMonth()]}<br>` + items.map((it) =>
        `${it.marker}${it.seriesName}: <b>${nf0.format(it.value[1])} km</b>`).join("<br>");
    };
    const recentYears = years.slice(-5);
    const last = recentYears.length - 1;
    o.series = recentYears.map((y, i) => line(String(y.year), y.points, i + 1, {
      step: "end",
      lineStyle: { width: i === last ? 3 : 2, color: series(i + 1) },
      // Direktbeschriftung nur für das laufende Jahr; die übrigen über die Legende
      endLabel: { show: i === last, color: css("--text-primary"), fontWeight: 600,
                  formatter: (p) => `${p.seriesName}: ${nf0.format(p.value[1])} km` },
    }));
    chart("chart-years").setOption(o, true);
  }

  function renderFtp(d) {
    const o = base();
    o.xAxis = Object.assign(o.xAxis, { type: "time",
      axisLabel: { color: css("--text-secondary"), formatter: "{MM}.{yyyy}" }, splitLine: { show: false } });
    o.yAxis = Object.assign(o.yAxis, { type: "value", scale: true });
    o.tooltip.valueFormatter = (v) => `${v} W`;
    const device = d.ftp.device.slice();
    // Treppenlinie bis heute fortführen, damit der aktuelle Wert sichtbar ist
    if (device.length) device.push([d.period.end, device[device.length - 1][1]]);
    o.series = [line("Gerät", device, 1, { step: "end" })];
    if (d.ftp.manual.length) {
      o.series.push({ name: "Manuell", type: "scatter", data: d.ftp.manual, symbolSize: 10,
        itemStyle: { color: series(2), borderColor: css("--surface-1"), borderWidth: 2 } });
    }
    chart("chart-ftp").setOption(o, true);
  }

  function activityTable(id, rows) {
    const head = `<thead><tr><th>Datum</th><th>Name</th><th>Art</th><th class="num">Dauer</th>
      <th class="num">km</th><th class="num">hm</th><th class="num">NP</th><th class="num">Ø HF</th>
      <th class="num">TSS</th></tr></thead>`;
    const body = rows.map((r) => `<tr class="clickable" data-activity="${r.id}" tabindex="0" title="Details anzeigen">
      <td>${fmtDate(r.date)} ${r.date.slice(11)}</td>
      <td>${esc(r.name) || '<span class="muted">–</span>'}</td>
      <td><span class="swatch" style="background:${series(CATEGORY_SLOT[r.category])}"></span>${r.category}</td>
      <td class="num">${fmtHours(r.hours)}</td>
      <td class="num">${nf1.format(r.km)}</td>
      <td class="num">${nf0.format(r.elevation_m)}</td>
      <td class="num">${r.np_w ? r.np_w + " W" : "–"}</td>
      <td class="num">${r.avg_hr ?? "–"}</td>
      <td class="num" title="${r.load_basis === "hr" ? "aus Herzfrequenz" : r.load_basis === "power" ? "aus Leistung" : ""}">${r.tss ?? "–"}${r.load_basis === "hr" ? "*" : ""}</td>
    </tr>`).join("");
    document.getElementById(id).innerHTML = rows.length ? head + `<tbody>${body}</tbody>`
      : `<tbody><tr><td class="muted">Keine Einträge im Zeitraum</td></tr></tbody>`;
  }

  // --- Erklärungen als Overlay -------------------------------------------------
  function infoButton(key) {
    return `<button class="info-btn" data-info="${key}" aria-label="Erklärung">i</button>`;
  }

  const dialog = document.getElementById("info-dialog");
  function openInfo(key) {
    const info = (window.TP_INFO || {})[key];
    if (!info) return;
    document.getElementById("info-title").textContent = info.title;
    document.getElementById("info-body").innerHTML = info.body;
    dialog.showModal();
  }
  // Ein Klick-Handler für alle (i)-Schaltflächen, auch für später gezeichnete Kacheln
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".info-btn");
    if (btn) { openInfo(btn.dataset.info); return; }
    if (e.target.closest(".info-close") || e.target === dialog) { dialog.close(); return; }
    const row = e.target.closest("tr[data-activity]");
    if (row && window.TP) window.TP.openActivity(row.dataset.activity);
  });
  // Tastatur: Zeile mit Enter oder Leertaste öffnen
  document.addEventListener("keydown", (e) => {
    const row = e.target.closest && e.target.closest("tr[data-activity]");
    if (row && (e.key === "Enter" || e.key === " ") && window.TP) {
      e.preventDefault();
      window.TP.openActivity(row.dataset.activity);
    }
  });

  // ---------------------------------------------------------------------------
  async function load() {
    document.querySelectorAll("[data-range]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.range === state.range)));
    const res = await fetch(`/api/dashboard?range=${state.range}`);
    const d = await res.json();
    const empty = d.kpis.activities === 0 && d.recent.length === 0;
    document.getElementById("empty").hidden = !empty;
    document.getElementById("content").hidden = empty;
    if (empty) return;

    document.getElementById("period").textContent = `${fmtDate(d.period.start)} – ${fmtDate(d.period.end)}`;
    renderKpis(d);
    renderFitness(d);
    renderWeekly(d);
    renderYears(d);
    renderFtp(d);
    activityTable("table-long", d.long_rides);
    activityTable("table-recent", d.recent);
  }

  document.querySelectorAll("[data-range]").forEach((b) => b.addEventListener("click", () => {
    state.range = b.dataset.range;
    localStorageSet("range", state.range);
    load();
  }));
  window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", load);
  load();
})();
