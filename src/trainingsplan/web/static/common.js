// Gemeinsame Bausteine aller Seiten: Erklärungs-Overlay und Öffnen von Aktivitäten.
(function () {
  "use strict";

  const TP = (window.TP = window.TP || {});

  TP.infoButton = (key) =>
    `<button class="info-btn" data-info="${key}" aria-label="Erklärung">i</button>`;

  TP.esc = (s) =>
    String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  TP.css = (name) => getComputedStyle(document.body).getPropertyValue(name).trim();

  const infoDialog = document.getElementById("info-dialog");
  TP.openInfo = (key) => {
    const info = (window.TP_INFO || {})[key];
    if (!info || !infoDialog) return;
    document.getElementById("info-title").textContent = info.title;
    document.getElementById("info-body").innerHTML = info.body;
    infoDialog.showModal();
  };

  // Ein Handler für alle (i)-Schaltflächen und anklickbaren Aktivitäten, auch für
  // Elemente, die erst später gezeichnet werden.
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".info-btn");
    if (btn) { e.stopPropagation(); TP.openInfo(btn.dataset.info); return; }
    if (e.target.closest(".info-close") || e.target === infoDialog) { infoDialog.close(); return; }
    const el = e.target.closest("[data-activity]");
    if (el && TP.openActivity) TP.openActivity(el.dataset.activity);
  });
  document.addEventListener("keydown", (e) => {
    const el = e.target.closest && e.target.closest("[data-activity]");
    if (el && (e.key === "Enter" || e.key === " ") && TP.openActivity) {
      e.preventDefault();
      TP.openActivity(el.dataset.activity);
    }
  });
})();
