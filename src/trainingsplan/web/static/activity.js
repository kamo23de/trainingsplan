// Detailansicht einer Aktivität als Overlay: Kennzahlen, Verläufe, Zonen,
// Bestwerte und Strecke. Wird aus den Tabellen über window.TP.openActivity(id) geöffnet.
(function () {
  "use strict";

  const nf0 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });
  const nf1 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const nf2 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const dialog = document.getElementById("activity-dialog");
  const body = document.getElementById("activity-body");
  let charts = [];

  const css = (name) => getComputedStyle(document.body).getPropertyValue(name).trim();
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function duration(sec) {
    if (sec == null) return "–";
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.round(sec % 60);
    return h ? `${h}:${String(m).padStart(2, "0")} h` : `${m}:${String(s).padStart(2, "0")} min`;
  }
  function dateTime(iso) {
    const d = new Date(iso);
    return d.toLocaleString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit",
      year: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  const info = (key) => `<button class="info-btn" data-info="${key}" aria-label="Erklärung">i</button>`;

  function tile(value, unit, label, key) {
    return `<div class="tile">${key ? info(key) : ""}<div class="value">${value}<span class="unit">${unit}</span></div>
      <div class="label">${label}</div></div>`;
  }

  const hoursText = (h) => (h >= 1 ? `${Math.floor(h)}:${String(Math.round((h % 1) * 60)).padStart(2, "0")} h` : `${Math.round(h * 60)} min`);

  // --- Passung zum Plan -------------------------------------------------------
  function complianceHtml(c) {
    if (!c) return "";
    if (c.score == null) {
      return `<section class="card compliance"><h2>Passung zum Plan ${info("compliance")}</h2>
        <p class="muted">${esc(c.note || "nicht bewertet")}</p></section>`;
    }
    const parts = c.parts ? Object.entries(c.parts).map(([label, [pts, max]]) => `
      <div class="cp-row"><span>${label}</span>
        <span class="cp-bar"><i style="width:${(pts / max) * 100}%"></i></span>
        <span class="cp-val">${nf1.format(pts)} / ${max}</span></div>`).join("") : "";
    const planned = c.planned_kind === "rest" ? "geplant: Ruhetag"
      : `geplant: <b>${esc(c.planned_title)}</b>${c.planned_hours ? ` · ${hoursText(c.planned_hours)}` : ""}${c.planned_tss ? ` · ${nf0.format(c.planned_tss)} TSS` : ""}`;
    return `<section class="card compliance">
      <h2>Passung zum Plan ${info("compliance")}</h2>
      <div class="cp-head">${TP.scoreBadge(c)}<span class="cp-rating">${esc(c.rating)}</span><span class="sub">${planned}</span></div>
      ${parts ? `<div class="cp-parts">${parts}</div>` : ""}
      ${c.note ? `<p class="cp-note">${esc(c.note)}</p>` : ""}
      ${c.planned_description ? `<details><summary>Geplante Vorgabe</summary><p>${esc(c.planned_description)}</p></details>` : ""}
    </section>`;
  }

  // --- Inhalt ----------------------------------------------------------------
  function render(d) {
    const s = d.summary;
    const category = s.category || s.sport;
    const basis = s.load_basis === "hr" ? " (aus HF)" : s.load_basis === "power" ? "" : "";

    const tiles = [
      tile(duration(s.moving_time_s), "", `Bewegungszeit · gesamt ${duration(s.elapsed_time_s)}`),
      tile(nf1.format(s.distance_km), "km", "Distanz"),
      tile(nf0.format(s.elevation_m), "hm", "Höhenmeter"),
      tile(s.avg_speed_kmh != null ? nf1.format(s.avg_speed_kmh) : "–", "km/h", "Ø Geschwindigkeit"),
    ];
    if (s.np_w && !s.is_ebike) {
      tiles.push(
        tile(nf0.format(s.avg_power_w ?? 0), "W", "Ø Leistung"),
        tile(nf0.format(s.np_w), "W", "Normalized Power", "np"),
        tile(s.if != null ? nf2.format(s.if) : "–", "", "Intensitätsfaktor (IF)", "if"),
      );
      if (s.work_kj != null) tiles.push(tile(nf0.format(s.work_kj), "kJ", "Arbeit", "work"));
    }
    tiles.push(
      tile(s.tss != null ? nf0.format(s.tss) : "–", "", `TSS${basis}`, "tss"),
      tile(s.avg_hr ?? "–", s.avg_hr ? "bpm" : "", s.max_hr ? `Ø Herzfrequenz · max ${s.max_hr}` : "Ø Herzfrequenz"),
    );

    const ref = [s.ftp_w ? `FTP ${s.ftp_w} W` : null, s.lthr_bpm ? `Schwellenpuls ${s.lthr_bpm} bpm` : null,
      s.device ? `Gerät: ${esc(s.device)}` : null, s.device_tss ? `Garmin-TSS ${s.device_tss}` : null]
      .filter(Boolean).join(" · ");

    let html = `
      <div class="act-head">
        <div>
          <h3>${esc(s.name) || "Aktivität"}</h3>
          <div class="sub">${dateTime(s.start_time)} · ${esc(category)}${ref ? " · " + ref : ""}</div>
        </div>
        <button class="act-close" aria-label="Schließen">×</button>
      </div>
      <section class="tiles act-tiles">${tiles.join("")}</section>
      ${complianceHtml(d.compliance)}`;

    if (d.raw_file_missing || !d.streams) {
      html += `<p class="muted">Für diese Aktivität liegt keine FIT-Datei vor, daher keine Verläufe.</p>`;
      body.innerHTML = html;
      return;
    }

    const st = d.streams;
    const hasPower = st.power.length > 0;
    html += `<div class="act-grid">
      <article class="card act-streams">
        <h2>Verlauf ${info("streams")}</h2>
        <p class="sub">über die Distanz in km</p>
        <div id="act-alt" class="chart xs"></div>
        <div id="act-speed" class="chart xs"></div>
        ${hasPower ? '<div id="act-power" class="chart xs"></div>' : ""}
        <div id="act-hr" class="chart xs"></div>
      </article>
      <article class="card act-route">
        <h2>Strecke</h2>
        <div id="act-map">${routeSvg(d.route)}</div>
      </article>
      ${hasPower && d.power_zones.length ? `<article class="card">
        <h2>Zeit in Leistungszonen ${info("power_zones")}</h2>
        <p class="sub">bezogen auf FTP ${s.ftp_w} W</p>
        <div id="act-pz" class="chart zones"></div></article>` : ""}
      ${d.hr_zones.length ? `<article class="card">
        <h2>Zeit in Herzfrequenzzonen ${info("hr_zones")}</h2>
        <p class="sub">bezogen auf Schwellenpuls ${s.lthr_bpm} bpm</p>
        <div id="act-hz" class="chart zones"></div></article>` : ""}
      ${d.best_efforts.length ? `<article class="card">
        <h2>Bestwerte dieser Fahrt ${info("best_efforts")}</h2>
        <table><thead><tr><th>Dauer</th><th class="num">Ø Leistung</th><th class="num">% FTP</th></tr></thead>
        <tbody>${d.best_efforts.map((e) => `<tr><td>${e.duration}</td><td class="num">${e.watts} W</td>
          <td class="num">${s.ftp_w ? nf0.format(e.watts / s.ftp_w * 100) + " %" : "–"}</td></tr>`).join("")}</tbody></table>
        </article>` : ""}
    </div>`;
    body.innerHTML = html;

    drawStreams(st, hasPower);
    if (hasPower && d.power_zones.length) drawZones("act-pz", d.power_zones, "W");
    if (d.hr_zones.length) drawZones("act-hz", d.hr_zones, "bpm");
  }

  // --- Verläufe: kleine Diagramme untereinander, gemeinsame x-Achse ------------
  function drawStreams(st, hasPower) {
    const x = st.distance_km.some((v) => v != null) ? st.distance_km : st.minutes;
    const unitX = x === st.distance_km ? "km" : "min";
    const defs = [
      ["act-alt", "Höhe", st.altitude, "m", css("--text-muted"), true],
      ["act-speed", "Geschwindigkeit", st.speed, "km/h", css("--series-3"), false],
      ...(hasPower ? [["act-power", "Leistung", st.power, "W", css("--series-1"), false]] : []),
      ["act-hr", "Herzfrequenz", st.hr, "bpm", css("--series-8"), false],
    ];
    const group = [];
    defs.forEach(([id, name, values, unit, color, area], i) => {
      const el = document.getElementById(id);
      if (!el) return;
      const c = echarts.init(el, null, { renderer: "svg" });
      const last = i === defs.length - 1;
      c.setOption({
        animation: false,
        grid: { left: 8, right: 12, top: 24, bottom: last ? 4 : 2, containLabel: true },
        title: { text: `${name} (${unit})`, left: 0, top: 0,
                 textStyle: { fontSize: 12, fontWeight: 500, color: css("--text-secondary") } },
        tooltip: { trigger: "axis", backgroundColor: css("--surface-1"), borderColor: css("--border"),
          textStyle: { color: css("--text-primary"), fontSize: 12 },
          axisPointer: { type: "line", lineStyle: { color: css("--text-muted") } },
          formatter: (items) => `${nf1.format(items[0].axisValue)} ${unitX}<br>${items[0].marker}${name}: <b>${items[0].value ?? "–"} ${unit}</b>` },
        xAxis: { type: "category", data: x, boundaryGap: false, axisTick: { show: false },
          axisLine: { lineStyle: { color: css("--grid") } },
          axisLabel: { show: last, color: css("--text-secondary"), formatter: (v) => nf0.format(v), interval: "auto" } },
        yAxis: { type: "value", scale: true, splitNumber: 2, splitLine: { lineStyle: { color: css("--grid") } },
          axisLabel: { color: css("--text-secondary"), formatter: (v) => nf0.format(v),
                       showMinLabel: false, showMaxLabel: false } },
        series: [{ type: "line", data: values, showSymbol: false, connectNulls: false,
          lineStyle: { width: area ? 1 : 1.5, color }, itemStyle: { color },
          areaStyle: area ? { color, opacity: 0.15 } : undefined }],
      });
      group.push(c);
    });
    echarts.connect(group);
    charts.push(...group);
  }

  // --- Zonen: Balken je Zone, Rampe einer Farbe hell → dunkel --------------------
  const RAMP = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#1c5cab", "#104281"];
  function drawZones(id, zones, unit) {
    const total = zones.reduce((sum, z) => sum + z.seconds, 0) || 1;
    const ramp = RAMP.slice(RAMP.length - zones.length);
    const c = echarts.init(document.getElementById(id), null, { renderer: "svg" });
    c.setOption({
      animation: false,
      grid: { left: 8, right: 88, top: 4, bottom: 4, containLabel: true },
      tooltip: { trigger: "item", backgroundColor: css("--surface-1"), borderColor: css("--border"),
        textStyle: { color: css("--text-primary"), fontSize: 12 },
        formatter: (p) => {
          const z = zones[p.dataIndex];
          const range = z.to ? `${z.from}–${z.to} ${unit}` : `ab ${z.from} ${unit}`;
          return `${z.zone}<br>${range}<br><b>${duration(z.seconds)}</b> (${nf0.format(z.seconds / total * 100)} %)`;
        } },
      xAxis: { type: "value", show: false },
      yAxis: { type: "category", inverse: true, data: zones.map((z) => z.zone),
        axisTick: { show: false }, axisLine: { show: false },
        axisLabel: { color: css("--text-secondary"), fontSize: 11 } },
      series: [{ type: "bar", barMaxWidth: 14,
        data: zones.map((z, i) => ({ value: z.seconds, itemStyle: { color: ramp[i], borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: "right", color: css("--text-secondary"), fontSize: 11,
          formatter: (p) => p.value ? `${duration(p.value)} · ${nf0.format(p.value / total * 100)} %` : "" } }],
    });
    charts.push(c);
  }

  // --- Strecke als einfache Linie (ohne Kartenhintergrund, funktioniert offline) --
  function routeSvg(points) {
    if (!points || points.length < 2) return `<p class="muted">Keine GPS-Daten</p>`;
    const lat0 = points.reduce((s, p) => s + p[0], 0) / points.length;
    const k = Math.cos(lat0 * Math.PI / 180);
    const xy = points.map(([la, lo]) => [lo * k, -la]);
    const xs = xy.map((p) => p[0]), ys = xy.map((p) => p[1]);
    const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const size = 300, pad = 12;
    const scale = (size - 2 * pad) / Math.max(maxX - minX, maxY - minY, 1e-9);
    const w = (maxX - minX) * scale + 2 * pad, h = (maxY - minY) * scale + 2 * pad;
    const pts = xy.map(([x, y]) => [(x - minX) * scale + pad, (y - minY) * scale + pad]);
    const path = pts.map((p) => p.map((v) => v.toFixed(1)).join(",")).join(" ");
    const [sx, sy] = pts[0], [ex, ey] = pts[pts.length - 1];
    return `<svg viewBox="0 0 ${w.toFixed(0)} ${h.toFixed(0)}" role="img" aria-label="Streckenverlauf">
      <polyline points="${path}" fill="none" stroke="${css("--series-1")}" stroke-width="2"
        stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${sx}" cy="${sy}" r="5" fill="${css("--series-3")}" stroke="${css("--surface-1")}" stroke-width="2"/>
      <circle cx="${ex}" cy="${ey}" r="5" fill="${css("--series-8")}" stroke="${css("--surface-1")}" stroke-width="2"/>
    </svg>
    <div class="legend-inline"><span><i style="background:${css("--series-3")}"></i>Start</span>
      <span><i style="background:${css("--series-8")}"></i>Ziel</span></div>`;
  }

  // --- Öffnen / Schließen -----------------------------------------------------
  function dispose() {
    charts.forEach((c) => c.dispose());
    charts = [];
  }

  async function openActivity(id) {
    dispose();
    body.innerHTML = `<p class="muted">Lade Aktivität …</p>`;
    dialog.showModal();
    try {
      const res = await fetch(`/api/activities/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      render(await res.json());
    } catch (err) {
      body.innerHTML = `<div class="act-head"><h3>Fehler</h3><button class="act-close" aria-label="Schließen">×</button></div>
        <p>Die Aktivität konnte nicht geladen werden (${esc(err.message)}).</p>`;
    }
  }

  dialog.addEventListener("click", (e) => {
    if (e.target === dialog || e.target.closest(".act-close")) dialog.close();
  });
  dialog.addEventListener("close", dispose);
  window.addEventListener("resize", () => charts.forEach((c) => c.resize()));

  window.TP = Object.assign(window.TP || {}, { openActivity });
})();
