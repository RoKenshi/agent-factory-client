#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"

sh -n "$ROOT/install.sh"
sh -n "$ROOT/uninstall.sh"
python3 "$ROOT/tests/test_pinned_release_key.py"
python3 -m unittest discover -s "$ROOT/tests" -p 'test_release_bundle.py'
sh "$ROOT/tests/test_install.sh"

case "$#" in
  0) ;;
  2) python3 "$ROOT/tools/verify_release.py" --version "$1" --directory "$2" ;;
  *) echo "usage: tools/release-check.sh [VERSION RELEASE_DIRECTORY]" >&2; exit 2 ;;
esac
