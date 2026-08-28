from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


def test_build_uses_python_312_and_recreates_its_virtualenv(tmp_path: Path) -> None:
    """Catch fallback to an unsupported Python or reuse of a mixed virtualenv."""
    script = tmp_path / "build.sh"
    shutil.copy2(PROJECT_ROOT / "build.sh", script)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    build_log = tmp_path / "python.log"
    _write_executable(
        fake_bin / "python3.12",
        """#!/bin/sh
printf '%s\n' "$*" >> "$BUILD_LOG"
mkdir -p .venv_build/bin
: > .venv_build/bin/activate
""",
    )
    _write_executable(fake_bin / "python3", "#!/bin/sh\nexit 81\n")
    _write_executable(fake_bin / "pip", "#!/bin/sh\nexit 0\n")
    _write_executable(
        fake_bin / "pyinstaller",
        "#!/bin/sh\nmkdir -p dist/PROCRASTINATOR.app\n",
    )

    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}:/usr/bin:/bin"
    environment["BUILD_LOG"] = str(build_log)
    result = subprocess.run(
        [str(script)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert build_log.read_text(encoding="utf-8") == "-m venv --clear .venv_build\n"
    assert (tmp_path / "dist" / "PROCRASTINATOR.app").is_dir()
