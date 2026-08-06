#!/bin/sh
set -eu

REPOSITORY="${AGENT_FACTORY_REPOSITORY:-RoKenshi/agent-factory-client}"
INSTALL_ROOT="${AGENT_FACTORY_INSTALL_ROOT:-$HOME/.local/share/agent-factory}"
BIN_DIR="${AGENT_FACTORY_BIN_DIR:-$HOME/.local/bin}"

command -v curl >/dev/null 2>&1 || { echo "error: curl is required" >&2; exit 1; }
command -v tar >/dev/null 2>&1 || { echo "error: tar is required" >&2; exit 1; }

case "$(uname -s)" in
  Darwin) platform="macos" ;;
  Linux) platform="linux" ;;
  *) echo "error: unsupported operating system" >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) architecture="x86_64" ;;
  arm64|aarch64) architecture="arm64" ;;
  *) echo "error: unsupported architecture" >&2; exit 1 ;;
esac

if [ "${AGENT_FACTORY_VERSION:-}" ]; then
  tag="${AGENT_FACTORY_VERSION}"
  case "$tag" in v*) ;; *) tag="v$tag" ;; esac
else
  latest="$(curl -fsSL -o /dev/null -w '%{url_effective}' "https://github.com/$REPOSITORY/releases/latest")"
  tag="${latest##*/}"
fi

version="${tag#v}"
asset="agent-factory-v${version}-${platform}-${architecture}.tar.gz"
base="https://github.com/$REPOSITORY/releases/download/$tag"
temporary="$(mktemp -d "${TMPDIR:-/tmp}/agent-factory-install.XXXXXX")"
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

curl -fL "$base/$asset" -o "$temporary/$asset"
curl -fL "$base/SHA256SUMS" -o "$temporary/SHA256SUMS"
expected="$(awk -v name="$asset" '$2 == name {print $1}' "$temporary/SHA256SUMS")"
[ -n "$expected" ] || { echo "error: release checksum is missing" >&2; exit 1; }

if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$temporary/$asset" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$temporary/$asset" | awk '{print $1}')"
fi
[ "$actual" = "$expected" ] || { echo "error: SHA-256 verification failed" >&2; exit 1; }

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
target="$INSTALL_ROOT/$version"
[ ! -e "$target" ] || { echo "error: $target already exists" >&2; exit 1; }
tar -xzf "$temporary/$asset" -C "$INSTALL_ROOT"
extracted="$INSTALL_ROOT/agent-factory-v${version}-${platform}-${architecture}"
mv "$extracted" "$target"
"$target/agent-factory" self-test
ln -sfn "$target/agent-factory" "$BIN_DIR/agent-factory"

echo "Agent Factory $version installed at $target"
echo "Ensure $BIN_DIR is in PATH, then run: agent-factory serve"
