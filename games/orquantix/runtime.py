from __future__ import annotations

import threading
from pathlib import Path

from downloader import download_all, missing_files
from games.orquantix import load_resources
from games.orquantix.state import OrquantixState


class OrquantixRuntime:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.state = OrquantixState()
        self._started = False
        self._lock = threading.Lock()

    @property
    def started(self) -> bool:
        with self._lock:
            return self._started

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        try:
            if missing_files(self.data_dir):
                self.state.update(
                    phase="downloading",
                    progress=0,
                    detail="Téléchargement…",
                )
                download_all(self.state, self.data_dir)
            load_resources(self.state, self.data_dir)
        except Exception as exc:  # noqa: BLE001 — remonté à l’interface
            self.state.update(phase="error", detail=f"Erreur : {exc}")
