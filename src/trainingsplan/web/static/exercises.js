// Übungskatalog für Rumpf-Stabi und Mobilität mit erklärenden Grafiken.
// Jede Grafik ist eine schlichte Figur aus Gelenkpunkten (Seitenansicht oder von oben):
// Endposition kräftig, Ausgangsposition hell, Bewegungsrichtung als Pfeil.
(function () {
  "use strict";

  // --- Übungen ---------------------------------------------------------------
  // Pose: head [x,y], sh (Schulter), hip, arms/legs: [[Ellbogen|Knie, Hand|Fuß], …]
  // Die erste Gliedmaße ist die vordere (kräftig), weitere sind die hinteren (heller).
  // torso: optionaler Kontrollpunkt für einen gekrümmten Rücken.
  const EX = {
    plank: {
      name: "Unterarmstütz",
      how: ["Ellbogen unter den Schultern, Unterarme parallel.",
        "Körper bildet eine Linie von Kopf bis Ferse, Bauchnabel leicht einziehen.",
        "Ruhig weiteratmen."],
      mistake: "Hüfte hängt durch oder ragt nach oben.",
      pose: { head: [56, 76], sh: [72, 84], hip: [148, 100], arms: [[[72, 114], [100, 114]]], legs: [[[184, 107], [218, 114]]] },
    },
    side_plank: {
      name: "Seitstütz",
      how: ["Seitlich auf den Unterarm, Ellbogen unter der Schulter.",
        "Füße übereinander, Hüfte anheben, bis der Körper eine Linie bildet.",
        "Freie Hand an die Hüfte oder nach oben strecken."],
      mistake: "Hüfte kippt nach hinten oder sinkt ab.",
      pose: { head: [60, 70], sh: [74, 82], hip: [146, 98], arms: [[[74, 114], [100, 114]], [[80, 60], [86, 36]]], legs: [[[182, 106], [218, 114]]] },
    },
    side_plank_lift: {
      name: "Seitstütz mit Hüftheben",
      how: ["Ausgangsposition wie beim Seitstütz.",
        "Hüfte langsam Richtung Boden senken und kraftvoll wieder anheben.",
        "Die Bewegung kommt aus der seitlichen Rumpfmuskulatur."],
      mistake: "Schwung holen oder in der Schulter einsinken.",
      pose: { head: [60, 70], sh: [74, 82], hip: [146, 98], arms: [[[74, 114], [100, 114]], [[110, 82], [140, 90]]], legs: [[[182, 106], [218, 114]]] },
      ghost: { head: [62, 74], sh: [74, 84], hip: [146, 112], arms: [], legs: [[[182, 114], [218, 115]]] },
      arrows: [[146, 114, 146, 96]],
    },
    dead_bug: {
      name: "Dead Bug",
      how: ["Rückenlage, Arme senkrecht nach oben, Knie und Hüfte im 90°-Winkel.",
        "Unteren Rücken fest in den Boden drücken.",
        "Gegengleich einen Arm nach hinten und ein Bein lang strecken, zurück, Seite wechseln."],
      mistake: "Hohlkreuz beim Strecken – nur so weit strecken, wie der Rücken am Boden bleibt.",
      pose: { head: [60, 104], sh: [78, 110], hip: [140, 110], arms: [[[80, 86], [82, 62]], [[60, 100], [38, 104]]], legs: [[[142, 78], [174, 78]], [[174, 104], [208, 108]]] },
      arrows: [[150, 66, 196, 92], [72, 54, 44, 88]],
    },
    bird_dog: {
      name: "Bird Dog",
      how: ["Vierfüßlerstand: Hände unter den Schultern, Knie unter der Hüfte.",
        "Gegengleich einen Arm nach vorn und ein Bein nach hinten strecken, bis beide waagerecht sind.",
        "Kurz halten, zurück, Seite wechseln."],
      mistake: "Becken kippt zur Seite oder das Bein geht zu hoch.",
      pose: { head: [62, 60], sh: [80, 72], hip: [150, 74], arms: [[[56, 68], [32, 64]], [[80, 94], [80, 116]]], legs: [[[184, 72], [218, 70]], [[150, 116], [184, 116]]] },
    },
    glute_bridge: {
      name: "Glute Bridge",
      how: ["Rückenlage, Füße hüftbreit aufgestellt, Arme neben dem Körper.",
        "Gesäß anspannen und das Becken heben, bis Knie, Hüfte und Schulter eine Linie bilden.",
        "Langsam wieder absenken."],
      mistake: "Ins Hohlkreuz drücken statt das Gesäß zu nutzen.",
      pose: { head: [52, 108], sh: [70, 112], hip: [132, 86], arms: [[[96, 115], [120, 115]]], legs: [[[168, 72], [176, 115]]] },
      ghost: { head: [52, 108], sh: [70, 112], hip: [132, 112], arms: [], legs: [[[160, 84], [176, 115]]] },
      arrows: [[126, 114, 126, 92]],
    },
    single_leg_bridge: {
      name: "Einbeinige Glute Bridge",
      how: ["Wie die Glute Bridge, aber ein Bein in Verlängerung des Oberschenkels strecken.",
        "Becken bleibt beim Heben waagerecht.",
        "Wiederholungen je Seite."],
      mistake: "Becken kippt zur Seite des gestreckten Beins.",
      pose: { head: [52, 108], sh: [70, 112], hip: [132, 86], arms: [[[96, 115], [120, 115]]], legs: [[[168, 72], [176, 115]], [[168, 74], [202, 62]]] },
      arrows: [[126, 114, 126, 92]],
    },
    hollow: {
      name: "Hollow Hold",
      how: ["Rückenlage, unteren Rücken in den Boden drücken.",
        "Schultern und gestreckte Beine leicht anheben, Arme lang über den Kopf.",
        "Position halten – je flacher, desto schwerer."],
      mistake: "Unterer Rücken löst sich vom Boden.",
      pose: { head: [70, 96], sh: [88, 104], hip: [132, 112], arms: [[[66, 94], [42, 86]]], legs: [[[166, 102], [202, 90]]] },
    },
    superman: {
      name: "Superman",
      how: ["Bauchlage, Arme nach vorn gestreckt.",
        "Arme, Brust und Beine gleichzeitig leicht anheben, Blick zum Boden.",
        "Kurz halten und kontrolliert ablegen."],
      mistake: "Kopf in den Nacken legen.",
      pose: { head: [62, 98], sh: [80, 106], hip: [150, 112], arms: [[[56, 98], [32, 90]]], legs: [[[184, 106], [218, 98]]] },
      ghost: { head: [60, 104], sh: [80, 110], hip: [150, 113], arms: [[[56, 112], [32, 113]]], legs: [[[184, 113], [218, 113]]] },
      arrows: [[24, 112, 24, 92], [226, 113, 226, 94]],
    },
    pallof: {
      name: "Pallof-Press",
      how: ["Band seitlich auf Brusthöhe befestigen, seitlich zum Befestigungspunkt stehen.",
        "Band mit beiden Händen vor der Brust halten, Knie leicht gebeugt.",
        "Arme langsam nach vorn strecken und zurückführen – der Rumpf darf sich nicht mitdrehen."],
      mistake: "Oberkörper dreht zum Band hin.",
      pose: { head: [140, 14], sh: [140, 30], hip: [140, 70], arms: [[[164, 42], [190, 42]]], legs: [[[136, 92], [134, 116]], [[146, 92], [150, 116]]] },
      ghost: { head: [140, 14], sh: [140, 30], hip: [140, 70], arms: [[[152, 50], [154, 40]]], legs: [] },
      band: [12, 42, 190, 42],
      arrows: [[160, 32, 192, 32]],
    },
    plank_tap: {
      name: "Stütz mit Schulterantippen",
      how: ["Hoher Stütz auf den Händen, Hände unter den Schultern, Füße etwas breiter.",
        "Abwechselnd mit einer Hand die gegenüberliegende Schulter antippen.",
        "Becken bleibt ruhig und waagerecht."],
      mistake: "Hüfte schaukelt hin und her.",
      pose: { head: [56, 64], sh: [72, 72], hip: [148, 94], arms: [[[72, 94], [72, 116]], [[94, 92], [78, 74]]], legs: [[[184, 104], [218, 114]]] },
    },
    ytw: {
      name: "Y-T-W",
      view: "top",
      how: ["Bauchlage (oder vorgebeugt), Stirn zum Boden, Daumen zeigen nach oben.",
        "Arme nacheinander in Y-, T- und W-Form vom Boden abheben.",
        "Schulterblätter dabei bewusst nach hinten unten ziehen."],
      mistake: "Schultern zu den Ohren ziehen.",
      top: true,
    },
    neck: {
      name: "Nacken-Isometrie",
      how: ["Aufrecht sitzen oder stehen, Hand an Stirn, Hinterkopf oder Schläfe.",
        "Kopf gegen die Hand drücken, ohne dass er sich bewegt – etwa halbe Kraft.",
        "Je Richtung 10 Sekunden halten."],
      mistake: "Zu viel Kraft oder Luft anhalten.",
      pose: { head: [140, 32], sh: [136, 50], hip: [134, 110], arms: [[[164, 66], [158, 32]]], legs: [] },
      arrows: [[178, 24, 162, 28], [112, 28, 128, 30]],
    },
    cat_cow: {
      name: "Katze-Kuh",
      how: ["Vierfüßlerstand.",
        "Ausatmen: Rücken rund machen, Kinn zur Brust (Katze).",
        "Einatmen: Brustbein nach vorn, leichtes Hohlkreuz (Kuh). Langsam im Wechsel."],
      mistake: "Bewegung nur im Nacken statt in der ganzen Wirbelsäule.",
      pose: { head: [64, 82], sh: [80, 74], hip: [150, 74], torso: [115, 44], arms: [[[80, 95], [80, 116]]], legs: [[[150, 116], [184, 116]]] },
      ghost: { head: [58, 60], sh: [80, 74], hip: [150, 74], torso: [115, 92], arms: [], legs: [] },
      arrows: [[115, 82, 115, 56]],
    },
    hip_flexor: {
      name: "Hüftbeuger-Dehnung",
      how: ["Ausfallschritt, hinteres Knie auf einer Unterlage.",
        "Becken aufrichten (Gesäß anspannen) und die Hüfte sanft nach vorn schieben.",
        "Dehnung vorn an der Hüfte des hinteren Beins, je Seite 45 Sekunden."],
      mistake: "Ins Hohlkreuz ausweichen statt das Becken aufzurichten.",
      pose: { head: [118, 16], sh: [118, 32], hip: [116, 76], arms: [[[106, 56], [92, 72]]], legs: [[[78, 78], [76, 116]], [[150, 114], [188, 116]]] },
      arrows: [[132, 90, 108, 90]],
    },
    open_book: {
      name: "BWS-Rotation (Open Book)",
      view: "top",
      how: ["Seitlage, Knie angewinkelt vor dem Körper, Arme nach vorn gestreckt.",
        "Oberen Arm in einem Bogen zur anderen Seite öffnen, Blick folgt der Hand.",
        "Knie bleiben zusammen am Boden. Langsam zurück."],
      mistake: "Knie heben vom Boden ab.",
      top: true,
    },
  };

  // --- Programme (Dosierung passend zu den Texten im Plan) ------------------
  const PROGRAMS = {
    "core-a": { title: "Rumpf A: Basis", rounds: "3 Runden, 30 s Pause zwischen den Übungen",
      items: [["plank", "45 s"], ["side_plank", "30 s je Seite"], ["dead_bug", "10× je Seite"],
        ["bird_dog", "10× je Seite"], ["glute_bridge", "15×"]] },
    "core-b": { title: "Rumpf B: Rotation & Hüfte", rounds: "3 Runden, kurze Pausen",
      items: [["hollow", "30 s"], ["side_plank_lift", "10× je Seite"], ["superman", "12×"],
        ["pallof", "10× je Seite"], ["single_leg_bridge", "10× je Seite"]] },
    "core-c": { title: "Rumpf C: Ultra-Spezial", rounds: "3 Runden, danach Dehnung",
      items: [["plank_tap", "16× (abwechselnd)"], ["ytw", "je 8×"], ["neck", "4 × 10 s je Richtung"],
        ["bird_dog", "10× je Seite"], ["hip_flexor", "45 s je Seite"]] },
    mobility: { title: "Mobilität & Rumpf leicht", rounds: "1 Runde, ruhig und ohne Ermüdung",
      items: [["cat_cow", "10×"], ["hip_flexor", "45 s je Seite"], ["open_book", "10× je Seite"],
        ["dead_bug", "2 × 8"], ["glute_bridge", "2 × 12"]] },
  };

  // --- Zeichnen --------------------------------------------------------------
  const css = (n) => getComputedStyle(document.body).getPropertyValue(n).trim();
  const P = (p) => `${p[0]},${p[1]}`;

  function figure(pose, ink, faded) {
    const parts = [];
    const limb = (a, b, c, op) => parts.push(
      `<polyline points="${P(a)} ${P(b)} ${P(c)}" fill="none" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="${op}"/>`);
    (pose.legs || []).slice(1).forEach(([k, f]) => limb(pose.hip, k, f, faded ? 0.18 : 0.45));
    (pose.arms || []).slice(1).forEach(([e, h]) => limb(pose.sh, e, h, faded ? 0.18 : 0.45));
    const op = faded ? 0.22 : 1;
    if (pose.torso) {
      parts.push(`<path d="M${P(pose.sh)} Q${P(pose.torso)} ${P(pose.hip)}" fill="none" stroke="${ink}" stroke-width="9" stroke-linecap="round" opacity="${op}"/>`);
    } else {
      parts.push(`<line x1="${pose.sh[0]}" y1="${pose.sh[1]}" x2="${pose.hip[0]}" y2="${pose.hip[1]}" stroke="${ink}" stroke-width="9" stroke-linecap="round" opacity="${op}"/>`);
    }
    parts.push(`<line x1="${pose.sh[0]}" y1="${pose.sh[1]}" x2="${pose.head[0]}" y2="${pose.head[1]}" stroke="${ink}" stroke-width="6" stroke-linecap="round" opacity="${op}"/>`);
    parts.push(`<circle cx="${pose.head[0]}" cy="${pose.head[1]}" r="9" fill="${ink}" opacity="${op}"/>`);
    (pose.legs || []).slice(0, 1).forEach(([k, f]) => limb(pose.hip, k, f, op));
    (pose.arms || []).slice(0, 1).forEach(([e, h]) => limb(pose.sh, e, h, op));
    return parts.join("");
  }

  function arrow(a, color, id) {
    return `<line x1="${a[0]}" y1="${a[1]}" x2="${a[2]}" y2="${a[3]}" stroke="${color}" stroke-width="2.5" marker-end="url(#${id})"/>`;
  }

  // Draufsichten für Übungen, die von der Seite nicht erkennbar sind
  function topView(key, ink, accent) {
    const body = (extra) => `
      <line x1="120" y1="40" x2="120" y2="92" stroke="${ink}" stroke-width="10" stroke-linecap="round"/>
      <line x1="104" y1="44" x2="136" y2="44" stroke="${ink}" stroke-width="7" stroke-linecap="round"/>
      <polyline points="114,92 110,108 108,124" fill="none" stroke="${ink}" stroke-width="7" stroke-linecap="round"/>
      <polyline points="126,92 130,108 132,124" fill="none" stroke="${ink}" stroke-width="7" stroke-linecap="round"/>
      <circle cx="120" cy="28" r="10" fill="${ink}"/>${extra}`;
    const arm = (pts, op) => `<polyline points="${pts}" fill="none" stroke="${ink}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" opacity="${op}"/>`;
    if (key === "ytw") {
      return body(
        arm("104,44 92,62 80,46", 0.25) + arm("136,44 148,62 160,46", 0.25) +   // W
        arm("104,44 84,44 64,44", 0.35) + arm("136,44 156,44 176,44", 0.35) +   // T
        arm("104,44 92,26 80,8", 1) + arm("136,44 148,26 160,8", 1)          // Y
      );
    }
    // Open Book: Seitlage von oben, Knie nach vorn (unten), oberer Arm öffnet
    return `
      <line x1="70" y1="60" x2="150" y2="60" stroke="${ink}" stroke-width="10" stroke-linecap="round"/>
      <circle cx="54" cy="60" r="10" fill="${ink}"/>
      <polyline points="150,60 152,94 184,98" fill="none" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
      ${arm("76,60 78,84 80,108", 0.4)}
      ${arm("76,60 78,84 82,104", 0.2)}
      ${arm("76,60 80,36 84,12", 1)}
      <path d="M96,100 Q126,58 98,18" fill="none" stroke="${accent}" stroke-width="2.5" marker-end="url(#arr-${key})"/>`;
  }

  function svgFor(key) {
    const ex = EX[key];
    const ink = css("--text-secondary") || "#52514e";
    const accent = css("--series-1") || "#2a78d6";
    const id = `arr-${key}`;
    const defs = `<defs><marker id="${id}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="${accent}"/></marker></defs>`;
    let inner;
    if (ex.top) {
      inner = topView(key, ink, accent);
    } else {
      const floor = `<line x1="6" y1="120" x2="234" y2="120" stroke="${css("--border") || "#ddd"}" stroke-width="2"/>`;
      const band = ex.band ? `<line x1="${ex.band[0]}" y1="${ex.band[1]}" x2="${ex.band[2]}" y2="${ex.band[3]}" stroke="${css("--series-2")}" stroke-width="3" stroke-dasharray="6 4"/>
        <rect x="${ex.band[0] - 6}" y="${ex.band[1] - 14}" width="6" height="28" fill="${ink}" opacity=".5"/>` : "";
      inner = floor + band + (ex.ghost ? figure(ex.ghost, ink, true) : "") + figure(ex.pose, ink, false) +
        (ex.arrows || []).map((a) => arrow(a, accent, id)).join("");
    }
    const view = ex.top ? `<text x="236" y="126" text-anchor="end" font-size="10" fill="${ink}">von oben</text>` : "";
    return `<svg viewBox="0 0 240 130" role="img" aria-label="${ex.name}">${defs}${inner}${view}</svg>`;
  }

  function renderProgram(program) {
    const p = PROGRAMS[program];
    if (!p) return "";
    return `<p class="ex-rounds"><b>${p.rounds}</b></p>
      <ol class="exercises">${p.items.map(([key, dose]) => {
        const ex = EX[key];
        return `<li class="exercise">
          <div class="ex-figure">${svgFor(key)}</div>
          <div class="ex-text">
            <div class="ex-head"><b>${ex.name}</b><span class="ex-dose">${dose}</span></div>
            <ul>${ex.how.map((h) => `<li>${h}</li>`).join("")}</ul>
            <p class="ex-mistake"><b>Achte darauf:</b> ${ex.mistake}</p>
          </div></li>`;
      }).join("")}</ol>`;
  }

  window.TP = window.TP || {};
  window.TP.exercises = { EX, PROGRAMS, svgFor, renderProgram };
})();
