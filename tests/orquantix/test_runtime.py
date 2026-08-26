from pathlib import Path

import games.orquantix.runtime as runtime_module
from games.orquantix.runtime import OrquantixRuntime


class ImmediateThread:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


def test_ensure_loaded_runs_only_once(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(runtime_module.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(
        runtime_module,
        "load_resources",
        lambda state, data_dir: calls.append((state, data_dir)),
    )
    runtime = OrquantixRuntime(tmp_path)

    runtime.ensure_loaded()
    runtime.ensure_loaded()

    assert runtime.started is True
    assert calls == [(runtime.state, tmp_path)]


def test_load_downloads_before_loading_when_files_are_missing(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: ["Lexique383.tsv"])
    monkeypatch.setattr(
        runtime_module,
        "download_all",
        lambda state, data_dir: calls.append("download"),
    )
    monkeypatch.setattr(
        runtime_module,
        "load_resources",
        lambda state, data_dir: calls.append("load"),
    )

    OrquantixRuntime(tmp_path)._load()

    assert calls == ["download", "load"]


def test_load_skips_download_when_files_are_present(monkeypatch, tmp_path: Path):
    calls = []
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(
        runtime_module,
        "download_all",
        lambda state, data_dir: calls.append("download"),
    )
    monkeypatch.setattr(
        runtime_module,
        "load_resources",
        lambda state, data_dir: calls.append("load"),
    )

    OrquantixRuntime(tmp_path)._load()

    assert calls == ["load"]


def test_load_failure_is_published_on_state(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime_module, "missing_files", lambda data_dir: [])

    def fail(state, data_dir):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(runtime_module, "load_resources", fail)
    runtime = OrquantixRuntime(tmp_path)

    runtime._load()

    assert runtime.state.phase == "error"
    assert "kaboom" in runtime.state.detail
