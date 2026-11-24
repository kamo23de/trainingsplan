// Erklärtexte für die Elemente des Dashboards. Angezeigt als Overlay (Dialog),
// geöffnet über die (i)-Schaltflächen. Inhalte sind HTML.
window.TP_INFO = {
  activities: {
    title: "Aktivitäten",
    body: `<p>Anzahl aller aufgezeichneten Aktivitäten im gewählten Zeitraum – Radfahrten,
      eBike-Fahrten und sonstige Sportarten zusammen.</p>`,
  },
  hours: {
    title: "Trainingszeit gesamt",
    body: `<p>Summe der Bewegungszeit aller Aktivitäten im Zeitraum. Gezählt wird die
      Zeit, in der das Gerät aufgezeichnet hat (ohne Pausen bei Auto-Pause).</p>`,
  },
  bike_km: {
    title: "Rad (ohne eBike)",
    body: `<p>Gefahrene Kilometer mit dem Rad im Zeitraum. eBike-Fahrten sind bewusst
      nicht enthalten, weil sie als Training anders zu bewerten sind.</p>`,
  },
  elevation: {
    title: "Höhenmeter",
    body: `<p>Summe der Anstiege aller Aktivitäten im Zeitraum, wie vom Gerät
      aufgezeichnet (barometrisch oder per GPS).</p>`,
  },
  bike_per_week: {
    title: "Rad pro Woche (Ø)",
    body: `<p>Durchschnittliche Radstunden pro Woche im Zeitraum, ohne eBike.
      Wochen ohne Training zählen mit, sofern sie zwischen der ersten und letzten
      Aktivität liegen.</p>`,
  },
  long_rides: {
    title: "Fahrten ab 4 h",
    body: `<p>Anzahl der Radfahrten mit mindestens 4 Stunden Bewegungszeit. Lange
      Fahrten sind für Ultradistanzen die wichtigste Einheit: Sie trainieren die
      Grundlagenausdauer, den Fettstoffwechsel, die Verpflegung und das Sitzen.</p>`,
  },
  longest: {
    title: "Längste Fahrt",
    body: `<p>Die Radfahrt mit der größten Distanz im gewählten Zeitraum.</p>`,
  },
  ctl: {
    title: "Fitness (CTL – Chronic Training Load)",
    body: `<p>Die <b>langfristige Trainingsbelastung</b>: ein gleitender Durchschnitt der
      täglichen Belastung (TSS) über etwa <b>42 Tage</b>, bei dem jüngere Tage stärker
      zählen. Ein CTL von 60 heißt: Du hast in den letzten Wochen im Schnitt etwa
      60 TSS pro Tag trainiert.</p>
      <p>Der Wert steigt langsam und sinkt langsam. Er beschreibt, wie viel Training
      dein Körper gewohnt ist – eine Näherung für deine aktuelle Fitness.</p>
      <p><b>Richtwert:</b> Ein Anstieg von etwa 3–7 Punkten pro Woche gilt als gut
      verträglich; deutlich mehr erhöht das Risiko von Übermüdung.</p>`,
  },
  atl: {
    title: "Ermüdung (ATL – Acute Training Load)",
    body: `<p>Die <b>kurzfristige Trainingsbelastung</b>: derselbe gleitende Durchschnitt,
      aber über nur etwa <b>7 Tage</b>. Er reagiert schnell auf einzelne harte
      Einheiten oder Ruhetage.</p>
      <p>Liegt die Ermüdung über der Fitness, trainierst du gerade mehr, als du
      gewohnt bist – das ist im Aufbau gewollt, aber nicht dauerhaft.</p>`,
  },
  tsb: {
    title: "Form (TSB – Training Stress Balance)",
    body: `<p><b>Form = Fitness − Ermüdung</b> (jeweils vom Vortag). Sie zeigt, wie
      ausgeruht du im Verhältnis zu deinem Trainingsniveau bist.</p>
      <table class="info-table">
        <tr><td>über +25</td><td>sehr ausgeruht, Fitness geht bereits verloren</td></tr>
        <tr><td>+5 bis +25</td><td>frisch – gut für Wettkämpfe und wichtige Events</td></tr>
        <tr><td>−10 bis +5</td><td>neutral, normales Training</td></tr>
        <tr><td>−10 bis −30</td><td>produktiver Trainingsreiz, spürbare Ermüdung</td></tr>
        <tr><td>unter −30</td><td>hohe Belastung, Risiko von Übertraining</td></tr>
      </table>
      <p class="muted">Die Grenzen sind Richtwerte und individuell verschieden.</p>`,
  },
  fitness_chart: {
    title: "Fitness und Ermüdung",
    body: `<p>Verlauf von <b>Fitness (CTL)</b> und <b>Ermüdung (ATL)</b> pro Tag. Beide
      werden aus der Trainingsbelastung (TSS) jeder Aktivität berechnet, über den
      gesamten Datenbestand – auch wenn ein kürzerer Zeitraum gewählt ist.</p>
      <p>Typisches Muster im Trainingsaufbau: Die Fitness steigt stufenweise, die
      Ermüdung schwankt darum herum. Vor einem Saisonhöhepunkt sinkt die Ermüdung
      deutlich (Tapering), während die Fitness nur wenig nachgibt.</p>
      <p>Mit der Maus über das Diagramm fahren zeigt die Werte eines Tages; das
      Form-Diagramm darunter folgt mit.</p>`,
  },
  form_chart: {
    title: "Form",
    body: `<p>Verlauf der <b>Form (TSB)</b> = Fitness − Ermüdung. Über der Nulllinie bist
      du erholt, darunter belastet. Längere Phasen deutlich unter −30 sind ein
      Warnsignal; vor wichtigen Events sollte die Form positiv sein.</p>`,
  },
  tss: {
    title: "TSS – Training Stress Score",
    body: `<p>Maß für die Belastung einer einzelnen Einheit. <b>100 TSS entsprechen einer
      Stunde mit voller Kraft an der FTP</b>.</p>
      <p><b>Mit Leistungsmesser:</b> TSS = Dauer (h) × IF² × 100, wobei der
      Intensitätsfaktor IF = Normalized Power ÷ FTP ist.</p>
      <p><b>Ohne Leistung (z. B. eBike, mit * markiert):</b> Näherung über die
      Herzfrequenz, IF = Ø Herzfrequenz ÷ Schwellenpuls. Diese Werte sind ungenauer
      und fallen tendenziell etwas höher aus.</p>`,
  },
  weekly_chart: {
    title: "Trainingsumfang pro Woche",
    body: `<p>Bewegungszeit pro Kalenderwoche (Montag bis Sonntag), gestapelt nach
      Sportart (Rad, eBike, Laufen, Rudern, Kraft, Sonstige). Der Tooltip zeigt zusätzlich die
      Kilometer und die Gesamtbelastung (TSS) der Woche.</p>
      <p>Hilfreich, um Regelmäßigkeit, Aufbau- und Entlastungswochen sowie
      Trainingslücken zu erkennen.</p>`,
  },
  years_chart: {
    title: "Raddistanz im Jahresvergleich",
    body: `<p>Kumulierte Radkilometer (ohne eBike) für jedes Kalenderjahr, aufgetragen
      über den Tag des Jahres. So siehst du, ob du im laufenden Jahr vor oder hinter
      den Vorjahren liegst. Das laufende Jahr ist hervorgehoben.</p>
      <p>Das erste Jahr ist unvollständig, wenn die Historie mitten im Jahr beginnt.</p>`,
  },
  ftp_chart: {
    title: "FTP-Verlauf",
    body: `<p><b>FTP (Functional Threshold Power)</b> ist die Leistung, die du etwa eine
      Stunde lang halten kannst. Sie ist die Bezugsgröße für Trainingszonen und
      für die Berechnung des TSS.</p>
      <p><b>Gerät:</b> der Wert, der beim Aufzeichnen auf dem Garmin eingestellt war
      (aus den FIT-Dateien). <b>Manuell:</b> Werte, die du mit
      <code>trainingsplan threshold-add</code> erfasst hast – sie haben Vorrang.</p>
      <p>Ist die FTP auf dem Gerät veraltet, sind die TSS-Werte zu hoch (FTP zu
      niedrig) oder zu niedrig (FTP zu hoch).</p>`,
  },
  long_table: {
    title: "Lange Fahrten",
    body: `<p>Alle Radfahrten ab 4 Stunden im gewählten Zeitraum, sortiert nach Distanz.</p>
      <p><b>NP (Normalized Power):</b> gewichtete Durchschnittsleistung, die
      Schwankungen berücksichtigt und die physiologische Belastung besser abbildet
      als der reine Mittelwert. Bei langen Fahrten liegt sie meist bei 60–75 % der FTP.</p>`,
  },
  recent_table: {
    title: "Letzte Aktivitäten",
    body: `<p>Die zwölf jüngsten Aktivitäten, unabhängig vom gewählten Zeitraum.
      TSS-Werte mit * wurden aus der Herzfrequenz berechnet.</p>`,
  },
  np: {
    title: "Normalized Power (NP)",
    body: `<p>Gewichtete Durchschnittsleistung. Kurze, harte Abschnitte zählen stärker als
      im einfachen Mittelwert, weil der Körper auf Leistungsspitzen überproportional
      reagiert. NP beschreibt daher die tatsächliche Belastung einer wechselhaften
      Fahrt besser als die Ø Leistung.</p>`,
  },
  if: {
    title: "Intensitätsfaktor (IF)",
    body: `<p>IF = Normalized Power ÷ FTP. Er zeigt, wie intensiv eine Fahrt im
      Verhältnis zu deiner Schwelle war.</p>
      <table class="info-table">
        <tr><td>unter 0,75</td><td>Grundlage, lange ruhige Fahrten</td></tr>
        <tr><td>0,75 – 0,85</td><td>Tempo, zügige Ausfahrten</td></tr>
        <tr><td>0,85 – 0,95</td><td>Sweet Spot, harte Gruppenfahrten</td></tr>
        <tr><td>über 0,95</td><td>Schwelle und Wettkampf</td></tr>
      </table>
      <p>Für Ultradistanzen liegt der IF typischerweise bei 0,55 – 0,70.</p>`,
  },
  work: {
    title: "Arbeit (kJ)",
    body: `<p>Insgesamt getretene Arbeit. Faustregel: Die Kilojoule am Pedal entsprechen
      grob den verbrauchten Kilokalorien, weil der Wirkungsgrad des Körpers (~22 %)
      und der Umrechnungsfaktor (1 kcal = 4,18 kJ) sich etwa aufheben. Hilfreich für
      die Planung der Verpflegung auf langen Fahrten.</p>`,
  },
  streams: {
    title: "Verlauf",
    body: `<p>Höhenprofil, Geschwindigkeit, Leistung und Herzfrequenz über die Distanz.
      Die Diagramme sind gekoppelt: Mit der Maus über eines fahren zeigt dieselbe
      Stelle in allen. Lange Fahrten sind für die Anzeige ausgedünnt.</p>
      <p>Ein Anstieg der Herzfrequenz bei gleichbleibender Leistung im Verlauf langer
      Fahrten (Cardiac Drift) ist ein Zeichen von Ermüdung, Hitze oder zu wenig
      Flüssigkeit.</p>`,
  },
  power_zones: {
    title: "Leistungszonen",
    body: `<p>Zeit in den sieben Leistungszonen nach Coggan, bezogen auf die FTP, die zum
      Zeitpunkt der Fahrt galt:</p>
      <table class="info-table">
        <tr><td>Z1 &lt; 55 %</td><td>aktive Erholung</td></tr>
        <tr><td>Z2 55–75 %</td><td>Grundlagenausdauer</td></tr>
        <tr><td>Z3 75–90 %</td><td>Tempo</td></tr>
        <tr><td>Z4 90–105 %</td><td>Schwelle</td></tr>
        <tr><td>Z5 105–120 %</td><td>VO2max</td></tr>
        <tr><td>Z6 120–150 %</td><td>anaerobe Kapazität</td></tr>
        <tr><td>Z7 &gt; 150 %</td><td>neuromuskulär, Sprints</td></tr>
      </table>
      <p>Pausen und Rollen ohne Treten zählen als 0 W und damit zu Z1.</p>`,
  },
  hr_zones: {
    title: "Herzfrequenzzonen",
    body: `<p>Zeit in fünf Herzfrequenzzonen nach Friel, bezogen auf den Schwellenpuls:</p>
      <table class="info-table">
        <tr><td>Z1 &lt; 81 %</td><td>Erholung</td></tr>
        <tr><td>Z2 81–90 %</td><td>Grundlagenausdauer</td></tr>
        <tr><td>Z3 90–94 %</td><td>Tempo</td></tr>
        <tr><td>Z4 94–100 %</td><td>Schwelle</td></tr>
        <tr><td>Z5 &gt; 100 %</td><td>hohe Intensität</td></tr>
      </table>`,
  },
  best_efforts: {
    title: "Bestwerte dieser Fahrt",
    body: `<p>Die höchste durchschnittliche Leistung, die innerhalb dieser Fahrt über die
      jeweilige Dauer gehalten wurde. Der 20-Minuten-Wert × 0,95 ist eine gängige
      Schätzung der FTP – allerdings nur, wenn die 20 Minuten wirklich voll gefahren
      wurden.</p>`,
  },
  events: {
    title: "Haupt- und Nebenevents",
    body: `<p><b>Hauptevents</b> (höchstens drei) sind deine Saisonhöhepunkte. Von ihnen aus
      wird der Plan rückwärts aufgebaut: Grundlage → Aufbau → spezifische Phase →
      Tapering. Nach jedem Hauptevent folgt Regeneration.</p>
      <p><b>Nebenevents</b> sind Aufbauevents, z. B. Brevets oder Radmarathons. Sie
      werden in den laufenden Plan eingebaut: Am Tag davor gibt es eine Vorbelastung
      oder Ruhe, danach ein bis zwei Erholungstage. Ihre Belastung zählt zum
      Wochenumfang.</p>
      <p>Events lassen sich jederzeit ändern oder löschen – auch direkt im Kalender per
      Klick. Der Plan wird danach sofort neu berechnet. Mehrtägige Events (z. B. ein
      Ultra über 9 Tage) bekommen eine Dauer in Tagen.</p>`,
  },
  availability: {
    title: "Verfügbare Zeit",
    body: `<p>Die maximale Trainingszeit je Wochentag. Der Plan verteilt die Wochenbelastung
      nur auf Tage mit verfügbarer Zeit; Tage mit 0 Stunden werden Ruhetage.</p>
      <p>Der Tag mit der meisten Zeit am Wochenende wird zur langen Ausfahrt. In der
      spezifischen Phase vor einem Ultra werden beide Wochenendtage lang
      (Back-to-back), um mehrtägige Belastung zu üben.</p>
      <p>Pendelfahrten mit dem eBike plant die App nicht ein, sie zählen aber über die
      Herzfrequenz zur tatsächlichen Belastung.</p>`,
  },
  projection: {
    title: "Prognose",
    body: `<p>Die gestrichelten Linien zeigen, wie sich Fitness (CTL), Ermüdung (ATL) und
      Form (TSB) entwickeln, wenn du den Plan so umsetzt. Senkrechte Linien markieren
      deine Events.</p>
      <p>Ziel ist eine stetig steigende Fitness und zum Start des Hauptevents eine
      positive Form (etwa +10 bis +25). Während eines mehrtägigen Events fällt die
      Form stark ins Negative – das ist erwartbar.</p>
      <p>Die Prognose ist ein Modell. Sie wird mit jeder neuen Aktivität aus Garmin neu
      berechnet und an das tatsächliche Training angepasst.</p>`,
  },
  calendar: {
    title: "Kalender",
    body: `<p><b>Absolvierte Aktivitäten</b> (mit farbigem Punkt) kommen aus Garmin – ein
      Klick öffnet die Details. <b>Geplante Einheiten</b> sind nach Intensität
      eingefärbt (hell = locker, dunkel = intensiv); ein Klick zeigt die genaue
      Vorgabe mit Wattbereichen.</p>
      <p>Die linke Spalte zeigt die Phase der Woche sowie geplante und tatsächliche
      Stunden und Belastung. Mit „+“ an einem freien Tag legst du dort ein Nebenevent
      an.</p>`,
  },
  phases: {
    title: "Trainingsphasen",
    body: `<table class="info-table">
        <tr><td>Grundlage</td><td>viel Zeit in Z2, eine Tempo-Einheit pro Woche; Fitness steigt um ca. 3 CTL/Woche</td></tr>
        <tr><td>Aufbau</td><td>Sweet Spot und Schwelle (bei Ultras) bzw. Schwelle und VO2max; ca. 4 CTL/Woche</td></tr>
        <tr><td>Spezifisch</td><td>eventnah: bei Ultras lange Back-to-back-Wochenenden; ca. 2 CTL/Woche</td></tr>
        <tr><td>Entlastung</td><td>jede 4. Woche ca. 60 % der Belastung, damit das Training wirkt</td></tr>
        <tr><td>Tapering</td><td>1–2 Wochen (Ultra: 2) vor dem Hauptevent Umfang reduzieren, Form aufbauen</td></tr>
        <tr><td>Event</td><td>Eventwoche mit Vorbelastung am Vortag</td></tr>
        <tr><td>Regeneration</td><td>1–2 Wochen nach dem Hauptevent sehr wenig Belastung</td></tr>
      </table>`,
  },
  season: {
    title: "Saisonübersicht",
    body: `<p>Die ganze Saison auf einen Blick: Phasen, Entlastungswochen (E), Events und
      die prognostizierte Fitness (CTL) bis nach dem letzten Hauptevent.</p>
      <p><b>Events verschieben:</b> ein Event mit der Maus nach links oder rechts ziehen.
      Beim Loslassen wird das neue Datum gespeichert und der ganze Plan neu berechnet –
      Phasen, Entlastungswochen, Kalender und Prognose passen sich an. Mit der
      Tastatur: Event anwählen (Tab), Pfeiltasten verschieben um einen Tag, mit
      Umschalt um eine Woche. Ein Klick ohne Ziehen öffnet das Event zum Bearbeiten.</p>
      <p><b>Entlastung und Nebenevents:</b> Fällt eine Entlastungswoche auf ein
      Nebenevent ab 150 km, wird sie um eine Woche nach hinten verschoben (↷). Das
      Event ist dann die Schlüsseleinheit, die Entlastung folgt direkt danach.</p>
      <p>Ein Klick auf eine Phase oder Woche zeigt den Monat im Kalender.</p>`,
  },
  cross_training: {
    title: "Ergänzungstraining",
    body: `<p>Abwechslung zum Rad, sinnvoll dosiert für ein Ultra-Ziel:</p>
      <table class="info-table">
        <tr><td>Indoor-Rudern</td><td>Ganzkörper-Ausdauer, schont Sitzfläche und Knie. Im Winter abwechselnd mit
          Laufen statt einer Grundlage unter der Woche, außerdem in Entlastungs- und Regenerationswochen.</td></tr>
        <tr><td>Laufen</td><td>Reiz für Knochen und Bindegewebe, den Radfahren nicht gibt. Startet als
          Lauf-Geh-Wechsel mit 30 min und wird langsam auf 45 min gesteigert. Im Aufbau jede zweite Woche.</td></tr>
        <tr><td>Rumpf-Stabi</td><td>15–20 min, 2× pro Woche mit einem Tag Abstand, im Wechsel Programm A (Basis),
          B (Rotation &amp; Hüfte) und C (Nacken, Schultern – für lange Stunden im Sattel).
          In leichten Wochen Mobilität.</td></tr>
      </table>
      <p>In der spezifischen Phase und im Tapering bleibt es beim Rad: Dann zählt die
      Spezifität. Rumpf-Stabi läuft weiter, nur weniger.</p>
      <p>Auch die Radeinheiten wechseln: Tempo, Sweet Spot und Schwelle in verschiedenen
      Formen, Grundlagen mit Trittfrequenz- oder Kraftausdauer-Teil, lange Fahrten mit
      Tempo-Abschnitt oder als Test von Ausrüstung und Verpflegung.</p>`,
  },
  cross_hours: {
    title: "Laufen, Rudern, Kraft",
    body: `<p>Stunden Ergänzungstraining im Zeitraum: Läufe, Indoor-Rudern und Kraft- bzw.
      Rumpftraining, so wie Garmin sie aufgezeichnet hat.</p>`,
  },
  categories: {
    title: "Nach Sportart",
    body: `<p>Die Aktivitäten werden anhand der Sportart eingeordnet, die Garmin in der
      FIT-Datei speichert:</p>
      <table class="info-table">
        <tr><td>Rad</td><td>Radfahren mit Muskelkraft (Straße, Gravel, MTB, Rolle)</td></tr>
        <tr><td>eBike</td><td>Fahrten mit eBike-Profil – Belastung aus der Herzfrequenz</td></tr>
        <tr><td>Laufen</td><td>Laufen, Trail, Laufband</td></tr>
        <tr><td>Rudern</td><td>Rudern, auch Indoor-Rudern am Gerät</td></tr>
        <tr><td>Kraft</td><td>Krafttraining, Rumpf-Stabi, Yoga, Pilates</td></tr>
        <tr><td>Sonstige</td><td>alles andere, z. B. Wandern oder Schwimmen</td></tr>
      </table>
      <p>Jede Sportart hat überall im Rückblick dieselbe Farbe.</p>`,
  },
  compliance: {
    title: "Passung zum Plan (0–10)",
    body: `<p>Beim Import aus Garmin wird jede Aktivität mit der Einheit verglichen, die für
      diesen Tag geplant war. Die Planung eines Tages wird dafür eingefroren, sobald der
      Tag beginnt – spätere Planänderungen verfälschen den Vergleich nicht.</p>
      <table class="info-table">
        <tr><td>Sportart · 2</td><td>passt genau 2, andere Ausdauersportart (z. B. Laufen statt Rad) 1</td></tr>
        <tr><td>Dauer · 3</td><td>voll bei geplanter Dauer, 0 bei weniger als 40 % oder mehr als 250 %</td></tr>
        <tr><td>Belastung · 3</td><td>dasselbe für den TSS</td></tr>
        <tr><td>Intensität · 2</td><td>Intensitätsfaktor im Zielbereich der Einheit (z. B. Grundlage 0,55–0,76)</td></tr>
      </table>
      <p><b>8–10</b> gut · <b>5–7,9</b> teilweise · <b>unter 5</b> abweichend. Training an einem
      geplanten Ruhetag ergibt 6 (locker und kurz) bzw. 3. eBike-Pendeln wird nicht
      bewertet, zusätzliche Einheiten ohne Plan ebenfalls nicht.</p>
      <p><b>Zuordnung:</b> Die Reihenfolge der Einheiten im Plan spielt keine Rolle. Eine
      Aktivität wird nur einer Einheit mit passender Sportart zugeordnet – ein
      Krafttraining also der Rumpf-Einheit, nie der Radeinheit. Ist das nicht eindeutig
      (zwei ähnliche Fahrten, oder Laufen statt Rudern), erscheint ein <b>?</b> und die App
      fragt nach. Eine von Hand festgelegte Zuordnung bleibt erhalten und lässt sich in der
      Detailansicht jederzeit ändern.</p>
      <p>Neu bewerten, z. B. nach Änderung der FTP: <code>uv run trainingsplan score</code></p>`,
  },
  garmin_transfer: {
    title: "Auf Garmin übertragen",
    body: `<p>Die Einheit wird als <b>FIT-Workout</b> mit allen Schritten erzeugt – Einfahren,
      Intervalle mit Wiederholungen, Ausfahren. Leistungsziele stehen in % FTP; das Gerät
      rechnet sie mit der dort eingestellten FTP in Watt um.</p>
      <p><b>Auf Gerät übertragen:</b> Ist ein Garmin-Gerät per USB als Laufwerk verbunden
      (Ordner <code>Garmin/NewFiles</code>), kopiert die App die Datei direkt dorthin. Nach
      dem Auswerfen erscheint das Workout auf dem Gerät unter Training › Workouts; bei
      manchen Geräten erst nach einem Neustart.</p>
      <p><b>Neuere Geräte</b> (z. B. Edge 840/1040) verbinden sich am Mac nicht als Laufwerk,
      sondern per MTP. Dann die FIT-Datei herunterladen und mit einem MTP-Programm (z. B.
      OpenMTP) nach <code>Garmin/NewFiles</code> oder <code>Garmin/Workouts</code> kopieren. Ein
      fester Zielordner lässt sich mit <code>TP_GARMIN_DEVICE_DIR</code> einstellen.</p>
      <p>Eine direkte Übertragung in den Garmin-Connect-Kalender ist mit dem persönlichen
      API-Schlüssel nicht möglich – Garmin bietet das nur Firmenpartnern an.</p>`,
  },
};
