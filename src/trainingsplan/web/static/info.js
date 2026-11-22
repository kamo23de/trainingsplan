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
      <b>Rad</b>, <b>eBike</b> und <b>Sonstigem</b>. Der Tooltip zeigt zusätzlich die
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
};
