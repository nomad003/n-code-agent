#!/usr/bin/env bash
# Shared helpers sourced by the other scripts. Not meant to be run directly.
set -euo pipefail

# Project root = parent of this scripts/ directory, resolved no matter the CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PY="$VENV_DIR/bin/python"

# Auto-load .env (e.g. LLM_API_KEY) if present. Existing env vars win, since we
# only set names that aren't already exported.
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

# Ensure the venv exists and deps are installed; create on first use.
ensure_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "[setup] .venv not found — creating it..."
    "$PROJECT_ROOT/scripts/setup.sh"
  fi
}

# Run the project's python with PROJECT_ROOT as CWD so relative paths resolve.
run_py() {
  cd "$PROJECT_ROOT"
  exec "$VENV_PY" "$@"
}

# --- Daemon control --------------------------------------------------------
# Generic start/stop/status/restart for a background python entrypoint.
# pid + log files live under <project>/logs/<name>.{pid,log}.
RUN_DIR="$PROJECT_ROOT/logs"

_pidfile() { echo "$RUN_DIR/$1.pid"; }
_logfile() { echo "$RUN_DIR/$1.log"; }

# _running <name> -> prints live PID (and returns 0) if the daemon is up.
_running() {
  local pf; pf="$(_pidfile "$1")"
  [[ -f "$pf" ]] || return 1
  local pid; pid="$(cat "$pf" 2>/dev/null || true)"
  [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null && { echo "$pid"; return 0; }
  rm -f "$pf"  # stale pidfile
  return 1
}

# daemon_start <name> <script.py> [args...]
daemon_start() {
  local name="$1"; shift
  ensure_venv
  mkdir -p "$RUN_DIR"
  local pid; if pid="$(_running "$name")"; then
    echo "[$name] already running (pid $pid)"; return 0
  fi
  cd "$PROJECT_ROOT"
  nohup "$VENV_PY" "$@" >>"$(_logfile "$name")" 2>&1 < /dev/null &
  local newpid=$!
  echo "$newpid" > "$(_pidfile "$name")"
  echo "[$name] started (pid $newpid), log: $(_logfile "$name")"
}

# daemon_stop <name>
daemon_stop() {
  local name="$1"
  local pid; if ! pid="$(_running "$name")"; then
    echo "[$name] not running"; return 0
  fi
  kill "$pid" 2>/dev/null || true
  # wait up to 10s for graceful exit, then SIGKILL.
  for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
    echo "[$name] force-killed (pid $pid)"
  else
    echo "[$name] stopped (pid $pid)"
  fi
  rm -f "$(_pidfile "$name")"
}

# daemon_status <name>
daemon_status() {
  local name="$1"
  local pid; if pid="$(_running "$name")"; then
    echo "[$name] running (pid $pid), log: $(_logfile "$name")"
  else
    echo "[$name] stopped"
  fi
}

# daemon_dispatch <name> <script.py> <cmd> -- handles start/stop/restart/status,
# or runs in the FOREGROUND when cmd is empty (keeps the old default behaviour).
daemon_dispatch() {
  local name="$1" script="$2" cmd="${3:-}"
  case "$cmd" in
    start)   daemon_start "$name" "$script" ;;
    stop)    daemon_stop "$name" ;;
    restart) daemon_stop "$name"; daemon_start "$name" "$script" ;;
    status)  daemon_status "$name" ;;
    ""|fg|foreground) run_py "$script" ;;  # foreground (exec)
    *) echo "usage: $(basename "$0") [start|stop|restart|status]  (no arg = foreground)" >&2; return 2 ;;
  esac
}
