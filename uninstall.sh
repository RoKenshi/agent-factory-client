#!/bin/sh
set -eu

INSTALL_ROOT="${AGENT_FACTORY_INSTALL_ROOT:-$HOME/.local/share/agent-factory}"
BIN_DIR="${AGENT_FACTORY_BIN_DIR:-$HOME/.local/bin}"
STATE_ROOT="${AGENT_FACTORY_STATE_ROOT:-}"

case "$INSTALL_ROOT" in
  ""|/|"$HOME") echo "error: refusing unsafe install root: $INSTALL_ROOT" >&2; exit 1 ;;
esac
case "${INSTALL_ROOT##*/}" in
  agent-factory) ;;
  *) echo "error: install root must end in agent-factory" >&2; exit 1 ;;
esac

command_path="$BIN_DIR/agent-factory"
if [ -L "$command_path" ]; then
  target="$(readlink "$command_path")"
  case "$target" in
    "$INSTALL_ROOT"/*) rm -f "$command_path" ;;
    *) echo "error: command link does not belong to this installation" >&2; exit 1 ;;
  esac
elif [ -e "$command_path" ]; then
  echo "error: refusing to remove a non-symlink command: $command_path" >&2
  exit 1
fi

if [ -d "$INSTALL_ROOT" ]; then
  rm -rf -- "$INSTALL_ROOT"
fi

if [ "${AGENT_FACTORY_PURGE_STATE:-0}" = "1" ]; then
  if [ -z "$STATE_ROOT" ]; then
    case "$(uname -s)" in
      Darwin) STATE_ROOT="$HOME/Library/Application Support/Agent Factory" ;;
      Linux) STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/agent-factory" ;;
      *) echo "error: set AGENT_FACTORY_STATE_ROOT to purge state" >&2; exit 1 ;;
    esac
  fi
  case "${STATE_ROOT##*/}" in
    "Agent Factory"|agent-factory) rm -rf -- "$STATE_ROOT" ;;
    *) echo "error: refusing unsafe state root: $STATE_ROOT" >&2; exit 1 ;;
  esac
  echo "Agent Factory binaries and local state removed"
else
  echo "Agent Factory binaries removed. Local settings, credentials and run state were preserved."
fi
