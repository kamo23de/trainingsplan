"""Belastungskennzahlen pro Aktivität.

- Power-TSS: Standardformel aus Normalized Power (NP), Intensity Factor (IF) und FTP.
- hrTSS: vereinfachte Näherung über die mittlere Herzfrequenz relativ zum
  Schwellenpuls. Wird für Fahrten ohne Leistungsmesser genutzt (z. B. eBike).
  Später ersetzbar durch eine Berechnung über die Zeit in Herzfrequenzzonen.
"""

from trainingsplan.storage.models import LoadBasis


def power_tss(duration_s: float, normalized_power_w: float, ftp_w: float) -> tuple[float, float]:
    """Gibt (TSS, IF) zurück. TSS = Dauer[h] * IF² * 100."""
    if duration_s <= 0 or ftp_w <= 0:
        raise ValueError("Dauer und FTP müssen positiv sein")
    intensity = normalized_power_w / ftp_w
    return duration_s / 3600 * intensity**2 * 100, intensity


def hr_tss(duration_s: float, avg_hr_bpm: float, lthr_bpm: float) -> tuple[float, float]:
    """Gibt (hrTSS, IF) zurück, Näherung mit IF = HF_mittel / Schwellenpuls."""
    if duration_s <= 0 or lthr_bpm <= 0:
        raise ValueError("Dauer und Schwellenpuls müssen positiv sein")
    intensity = avg_hr_bpm / lthr_bpm
    return duration_s / 3600 * intensity**2 * 100, intensity


def compute_load(
    *,
    duration_s: float | None,
    normalized_power_w: float | None,
    avg_hr_bpm: float | None,
    ftp_w: float | None,
    lthr_bpm: float | None,
    is_ebike: bool = False,
) -> tuple[LoadBasis, float | None, float | None]:
    """Wählt die passende Grundlage und gibt (Grundlage, TSS, IF) zurück.

    Bei eBike-Fahrten wird bewusst die Herzfrequenz verwendet, da eine eventuell
    vorhandene Leistungsangabe die Motorunterstützung enthalten kann.
    """
    if not duration_s:
        return LoadBasis.NONE, None, None
    if not is_ebike and normalized_power_w and ftp_w:
        tss, intensity = power_tss(duration_s, normalized_power_w, ftp_w)
        return LoadBasis.POWER, tss, intensity
    if avg_hr_bpm and lthr_bpm:
        tss, intensity = hr_tss(duration_s, avg_hr_bpm, lthr_bpm)
        return LoadBasis.HEART_RATE, tss, intensity
    return LoadBasis.NONE, None, None
