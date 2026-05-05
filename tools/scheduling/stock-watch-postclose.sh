#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p runs/scheduler
LOG_PATH="runs/scheduler/postclose.log"

preferred_python="/Users/tokuzfunpi/codes/nvidia/311env/bin/python"
python_bin="python3.11"
if [[ -x "$preferred_python" ]]; then
  if "$preferred_python" -c "import pandas" >/dev/null 2>&1; then
    python_bin="$preferred_python"
  fi
elif [[ -x ".venv/bin/python" ]]; then
  if .venv/bin/python -c "import pandas" >/dev/null 2>&1; then
    python_bin=".venv/bin/python"
  fi
fi

{
  echo "=== stock-watch postclose ==="
  echo "started_at=$(TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "mode=postclose"
  echo "repo_root=$REPO_ROOT"
  echo "python=$python_bin"
  echo "watchlist_force=postclose-default"
  echo "command=$python_bin -m stock_watch daily --mode postclose --all-dates --max-days 60"
  # Keep evaluation history updated as older horizons mature.
  "$python_bin" -m stock_watch daily --mode postclose --all-dates --max-days 60

  # Yahoo/TW tickers sometimes lag after close; retry evaluation if the latest snapshot date
  # still has signal_date_missing rows or has not landed in outcomes yet.
  for attempt in 1 2 3 4; do
    probe_output="$(
      "$python_bin" - <<'PY'
from pathlib import Path

from verification.workflows.run_daily_verification import probe_postclose_evaluation_status

probe = probe_postclose_evaluation_status(
    snapshot_csv=Path("runs/verification/watchlist_daily/reco_snapshots.csv"),
    outcomes_csv=Path("runs/verification/watchlist_daily/reco_outcomes.csv"),
)
status = str(probe.get("status", "")).strip() or "unavailable"
target_signal_date = str(probe.get("target_signal_date", "")).strip()
missing_count = int(probe.get("missing_count", 0) or 0)
detail = str(probe.get("detail", "")).strip().replace("\t", " ")

print("\t".join([status, target_signal_date, str(missing_count), detail]))
PY
    )"
    IFS=$'\t' read -r probe_status target_signal_date missing_count probe_detail <<< "$probe_output"

    if [[ "$probe_status" == "ok" ]]; then
      echo "eval_retry=ok target_signal_date=${target_signal_date:-unknown} attempt=$attempt"
      break
    fi

    if [[ "$probe_status" == "signal_date_missing" ]]; then
      echo "eval_retry=signal_date_missing target_signal_date=${target_signal_date:-unknown} count=$missing_count attempt=$attempt"
    else
      echo "eval_retry=$probe_status target_signal_date=${target_signal_date:-unknown} detail=${probe_detail:-n/a} attempt=$attempt"
    fi

    if [[ "$attempt" -lt 4 ]]; then
      sleep 600
      "$python_bin" -m stock_watch verification daily --mode postclose --all-dates --max-days 60
    fi
  done

  # Backup verification history outside the repo (so `runs/` cleanup won't erase it).
  archive_dir="/Users/tokuzfunpi/.codex/automations/stock-watch-backup/archives/$(TZ=Asia/Taipei date '+%Y%m%d')"
  mkdir -p "$archive_dir"
  cp -f "runs/verification/watchlist_daily/reco_snapshots.csv" "$archive_dir/reco_snapshots.csv" 2>/dev/null || true
  cp -f "runs/verification/watchlist_daily/reco_outcomes.csv" "$archive_dir/reco_outcomes.csv" 2>/dev/null || true

  echo "doctor_command=$python_bin -m stock_watch doctor --skip-network --fail-on warn"
  "$python_bin" -m stock_watch doctor --skip-network --fail-on warn
  if [[ -f "runs/theme_watchlist_daily/local_doctor_summary.txt" ]]; then
    echo "doctor_summary=$(tr -d '\n' < runs/theme_watchlist_daily/local_doctor_summary.txt)"
  fi

  echo "finished_at=$(TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S %Z')"
} >>"$LOG_PATH" 2>&1
