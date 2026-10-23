#!/usr/bin/env bash
#
# Deploy-Skript für den Favicon Generator (FastAPI).
#
# Holt den aktuellen Stand von origin/$DEPLOY_BRANCH, installiert die
# Abhängigkeiten in ein virtuelles Environment, führt die Tests aus und
# startet den systemd-Dienst neu, der uvicorn betreibt. NGINX leitet
# https://kodinitools.com/<pfad>/ per proxy_pass an diesen Dienst weiter.
#
# Hinweis NGINX: Navigation, Footer und Cookie-Banner sind SSI-Includes
# (<!--#include virtual="/partials/..." -->) in static/index.html. Sie
# erscheinen nur, wenn die proxy_pass-Location `ssi on;` gesetzt hat.
#
# ------------------------------------------------------------------------
# Aufruf (auf dem Server, aus dem Repo-Verzeichnis):
#   ./deploy.sh
#
# Konfiguration über Umgebungsvariablen (optional):
#   DEPLOY_BRANCH  Branch                    (Default: main)
#   VENV_DIR       virtuelles Environment    (Default: <repo>/.venv)
#   PYTHON         Python für das venv       (Default: python3)
#   SERVICE_NAME   systemd-Dienst            (Default: favicon-tool; leer = kein Neustart)
#   HEALTH_URL     Prüf-URL nach dem Neustart (Default: http://127.0.0.1:8005/; leer = überspringen)
#   RUN_TESTS      Tests laufen lassen       (Default: 1; auf 0 zum Überspringen)
#
# Beispiel:
#   SERVICE_NAME=favicon HEALTH_URL=http://127.0.0.1:8010/ ./deploy.sh
#
# Voraussetzungen auf dem Server: git, python3 (mit venv), curl,
# systemd-Unit für uvicorn, z. B.:
#   ExecStart=<repo>/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8005
#   WorkingDirectory=<repo>
# ------------------------------------------------------------------------
#
# Hinweis: Die gesamte Logik steht in main() und wird erst am Dateiende
# aufgerufen. Dadurch ist das komplette Skript geparst und im Speicher,
# bevor 'git reset --hard' die Datei auf der Platte ggf. verändert –
# so kann sich das laufende Skript nicht selbst beschädigen.

set -euo pipefail

main() {
  # ---- Konfiguration ------------------------------------------------------
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$SCRIPT_DIR"

  local BRANCH="${DEPLOY_BRANCH:-main}"
  local VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"
  local PYTHON="${PYTHON:-python3}"
  local SERVICE="${SERVICE_NAME-favicon-tool}"
  local HEALTH_URL="${HEALTH_URL-http://127.0.0.1:8005/}"
  local RUN_TESTS="${RUN_TESTS:-1}"

  echo "==> Repo:    $SCRIPT_DIR"
  echo "==> Branch:  $BRANCH"
  echo "==> venv:    $VENV_DIR"
  echo "==> Dienst:  ${SERVICE:-(kein Neustart)}"

  # ---- Werkzeuge prüfen ---------------------------------------------------
  local tool
  for tool in git "$PYTHON"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      echo "!! Benötigtes Programm nicht gefunden: $tool" >&2
      exit 1
    fi
  done
  if [[ -n "$SERVICE" ]] && ! command -v systemctl >/dev/null 2>&1; then
    echo "!! systemctl nicht gefunden (SERVICE_NAME= setzen, um den Neustart zu überspringen)." >&2
    exit 1
  fi
  if [[ -n "$HEALTH_URL" ]] && ! command -v curl >/dev/null 2>&1; then
    echo "!! curl nicht gefunden (HEALTH_URL= setzen, um die Prüfung zu überspringen)." >&2
    exit 1
  fi

  # ---- 1. Aktuellen Stand von origin/$BRANCH holen ------------------------
  echo "==> Hole aktuellen Stand von origin/$BRANCH ..."
  git fetch --prune origin "$BRANCH"
  git checkout -f "$BRANCH"
  git reset --hard "origin/$BRANCH"

  local COMMIT
  COMMIT="$(git rev-parse --short HEAD)"
  echo "==> Deploye Commit: $COMMIT"

  # ---- 2. Abhängigkeiten im venv -----------------------------------------
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "==> Lege virtuelles Environment an ..."
    "$PYTHON" -m venv "$VENV_DIR"
  fi
  local VPY="$VENV_DIR/bin/python"

  echo "==> Installiere Abhängigkeiten ..."
  "$VPY" -m pip install --quiet --upgrade pip
  if [[ "$RUN_TESTS" != "0" ]]; then
    "$VPY" -m pip install --quiet -r requirements-dev.txt
  else
    "$VPY" -m pip install --quiet -r requirements.txt
  fi

  # ---- 3. Tests (optional) ------------------------------------------------
  if [[ "$RUN_TESTS" != "0" ]]; then
    echo "==> Führe Tests aus (RUN_TESTS=0 zum Überspringen) ..."
    "$VPY" -m pytest -q
  else
    echo "==> Tests übersprungen (RUN_TESTS=0)."
  fi

  # ---- 4. Dienst neu starten ---------------------------------------------
  # index.html wird beim Start eingelesen, deshalb ist ein Neustart nötig.
  if [[ -n "$SERVICE" ]]; then
    echo "==> Starte Dienst $SERVICE neu ..."
    systemctl restart "$SERVICE"
  fi

  # ---- 5. Erreichbarkeit prüfen ------------------------------------------
  if [[ -n "$HEALTH_URL" ]]; then
    echo "==> Prüfe $HEALTH_URL ..."
    local attempt
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
      if curl -fsS -o /dev/null "${HEALTH_URL%/}/health" \
        && curl -fsS -o /dev/null "$HEALTH_URL" \
        && curl -fsS -o /dev/null "${HEALTH_URL%/}/static/design-system/tokens-v2.css"; then
        echo ""
        echo "==> Fertig. Commit $COMMIT läuft."
        return 0
      fi
      sleep 1
    done
    echo "!! $HEALTH_URL antwortet nicht. Log: journalctl -u ${SERVICE:-<dienst>} -n 50" >&2
    exit 1
  fi

  echo ""
  echo "==> Fertig. Commit $COMMIT ist ausgerollt (ohne Erreichbarkeitsprüfung)."
}

main "$@"
