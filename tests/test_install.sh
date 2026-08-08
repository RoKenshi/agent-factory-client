#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TEMPORARY="$(mktemp -d "${TMPDIR:-/tmp}/agent-factory-installer-test.XXXXXX")"
cleanup() {
  rm -rf "$TEMPORARY"
}
trap cleanup EXIT HUP INT TERM

case "$(uname -s)" in
  Darwin) platform="macos"; extension="zip" ;;
  Linux) platform="linux"; extension="tar.gz" ;;
  *) echo "unsupported test platform" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) architecture="x86_64" ;;
  arm64|aarch64) architecture="arm64" ;;
  *) echo "unsupported test architecture" >&2; exit 1 ;;
esac

version="9.8.7"
directory="agent-factory-v${version}-${platform}-${architecture}"
release="$TEMPORARY/release"
staging="$TEMPORARY/staging/$directory"
mkdir -p "$release" "$staging"
cat > "$staging/agent-factory" <<'BINARY'
#!/bin/sh
[ "${1:-}" = "self-test" ] || exit 2
printf '%s\n' '{"status":"ok"}'
BINARY
chmod +x "$staging/agent-factory"

asset="$directory.$extension"
if [ "$extension" = "zip" ]; then
  (cd "$TEMPORARY/staging" && zip -qr "$release/$asset" "$directory")
else
  tar -czf "$release/$asset" -C "$TEMPORARY/staging" "$directory"
fi
if command -v sha256sum >/dev/null 2>&1; then
  digest="$(sha256sum "$release/$asset" | awk '{print $1}')"
else
  digest="$(shasum -a 256 "$release/$asset" | awk '{print $1}')"
fi
printf '%s  %s\n' "$digest" "$asset" > "$release/SHA256SUMS"
openssl genpkey -quiet -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$TEMPORARY/private.pem"
openssl pkey -in "$TEMPORARY/private.pem" -pubout -out "$TEMPORARY/public.pem"
openssl dgst -sha256 -sign "$TEMPORARY/private.pem" \
  -out "$release/SHA256SUMS.sig" "$release/SHA256SUMS"

base="file://$release"

AGENT_FACTORY_VERSION="$version" \
AGENT_FACTORY_RELEASE_BASE_URL="$base" \
AGENT_FACTORY_RELEASE_PUBLIC_KEY_FILE="$TEMPORARY/public.pem" \
AGENT_FACTORY_INSTALL_ROOT="$TEMPORARY/install" \
AGENT_FACTORY_BIN_DIR="$TEMPORARY/bin" \
AGENT_FACTORY_NO_SETUP=1 \
  sh "$ROOT/install.sh"
"$TEMPORARY/bin/agent-factory" self-test

AGENT_FACTORY_VERSION="$version" \
AGENT_FACTORY_RELEASE_BASE_URL="$base" \
AGENT_FACTORY_RELEASE_PUBLIC_KEY_FILE="$TEMPORARY/public.pem" \
AGENT_FACTORY_INSTALL_ROOT="$TEMPORARY/install" \
AGENT_FACTORY_BIN_DIR="$TEMPORARY/bin" \
AGENT_FACTORY_NO_SETUP=1 \
  sh "$ROOT/install.sh"

printf 'tampered' > "$release/SHA256SUMS.sig"
if AGENT_FACTORY_VERSION="$version" \
  AGENT_FACTORY_RELEASE_BASE_URL="$base" \
  AGENT_FACTORY_RELEASE_PUBLIC_KEY_FILE="$TEMPORARY/public.pem" \
  AGENT_FACTORY_INSTALL_ROOT="$TEMPORARY/tampered-install" \
  AGENT_FACTORY_BIN_DIR="$TEMPORARY/tampered-bin" \
  AGENT_FACTORY_NO_SETUP=1 \
    sh "$ROOT/install.sh" >/dev/null 2>&1; then
  echo "installer accepted a tampered signature" >&2
  exit 1
fi
