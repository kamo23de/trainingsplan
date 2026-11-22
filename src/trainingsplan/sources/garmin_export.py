"""Einmaliger Import der Historie aus dem Garmin-Datenexport.

Der Export (ZIP aus dem Garmin-Konto) enthält die Original-FIT-Dateien,
teils selbst in weiteren ZIP-Archiven verschachtelt. Diese Funktion findet alle
FIT-Dateien unterhalb eines Verzeichnisses bzw. in ZIP-Archiven.
"""

import io
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FitSource:
    name: str  # eindeutiger Name innerhalb des Exports, dient als source_id
    data: bytes


def iter_fit_files(root: Path) -> Iterator[FitSource]:
    """Liefert alle FIT-Dateien unterhalb von ``root`` (auch aus ZIP-Archiven)."""
    for path in sorted(root.rglob("*")):
        suffix = path.suffix.lower()
        if suffix == ".fit":
            yield FitSource(name=path.relative_to(root).as_posix(), data=path.read_bytes())
        elif suffix == ".zip":
            yield from _iter_zip(path, prefix=path.relative_to(root).as_posix())


def _iter_zip(path: Path, prefix: str) -> Iterator[FitSource]:
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = f"{prefix}!{info.filename}"
            lower = info.filename.lower()
            if lower.endswith(".fit"):
                yield FitSource(name=name, data=archive.read(info))
            elif lower.endswith(".zip"):
                # verschachtelte Archive (im Garmin-Export üblich)
                nested = archive.read(info)
                with zipfile.ZipFile(io.BytesIO(nested)) as inner:
                    for inner_info in inner.infolist():
                        if inner_info.filename.lower().endswith(".fit"):
                            yield FitSource(
                                name=f"{name}!{inner_info.filename}",
                                data=inner.read(inner_info),
                            )
