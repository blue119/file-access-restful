#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'USAGE'
Usage: ./run.sh <command>

Commands:
  install   Synchronize dependencies with uv (including dev tools).
  lint      Run Ruff and Black checks through uv.
  run       Start the FastAPI dev server on a random port between 10000-20000.
  help      Show this help message.
USAGE
}

# random_port generates a random port between 10000 and 20000
random_port() {
    echo $(( RANDOM % 10000 + 10000 ))
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: '$1' is not installed or not on PATH" >&2
    exit 1
  fi
}

main() {
  if [[ $# -lt 1 ]]; then
    show_help
    exit 1
  fi

  case "$1" in
    install)
      require_command uv
      uv sync --dev
      ;;
    lint)
      require_command uv
      uv run ruff check src
      uv run black --check src
      ;;
    run)
      require_command uv
      PORT=$(random_port)
      echo "Serving on http://localhost:${PORT}"
      uv run uvicorn src.api.main:app --port "${PORT}"
      ;;
    help|-h|--help)
      show_help
      ;;
    *)
      echo "Unknown command: $1" >&2
      show_help
      exit 1
      ;;
  esac
}

main "$@"
