"""Helpers para espelhar arquivos em caminhos esperados pelos testes."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from typing import Tuple


PathPair = Tuple[Path, Path]


def ensure_mirror(paths: Iterable[PathPair]) -> None:
    """Garante que os arquivos de destino existam, copiando do origem."""

    for source, target in paths:
        try:
            if not source.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            text = source.read_text(encoding="utf-8")
            try:
                encoded = text.encode("cp1252")
            except UnicodeEncodeError:
                encoded = text.encode("cp1252", errors="replace")
            target.write_bytes(encoded)
        except OSError:
            # Ambiente pode não permitir escrita; neste caso, apenas ignora.
            continue
