#!/usr/bin/env bash
set -euo pipefail

VENV=".venv_build"
APP="PROCRASTINATOR"
# Pas d'icône PROCRASTINATOR pour l'instant : on garde l'icône Orquantix
# existante plutôt que d'en inventer une.
ICON="build_assets/Orquantix.icns"

echo "=== Creating build virtualenv ==="
python3.12 -m venv --clear "$VENV"
# shellcheck disable=SC1090
source "$VENV/bin/activate"

echo "=== Installing dependencies ==="
pip install --upgrade pip --quiet
pip install flask gensim pyinstaller requests unidecode pywebview rapidfuzz --quiet

echo "=== Running PyInstaller ==="
pyinstaller \
  --noconfirm \
  --onedir \
  --windowed \
  --name "$APP" \
  --icon "$ICON" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --collect-all gensim \
  --collect-all scipy \
  --hidden-import "gensim.models.keyedvectors" \
  --hidden-import "gensim.models.word2vec" \
  --hidden-import "scipy.sparse.csgraph._validation" \
  --collect-all pywebview \
  --hidden-import "webview" \
  main.py

echo ""
echo "=== Build complete ==="
echo "    App: dist/${APP}.app"
echo "    To use: open dist/${APP}.app  (or double-click in Finder)"
