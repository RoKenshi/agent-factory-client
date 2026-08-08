#!/bin/sh
set -eu

REPOSITORY="${AGENT_FACTORY_REPOSITORY:-RoKenshi/agent-factory-client}"
INSTALL_ROOT="${AGENT_FACTORY_INSTALL_ROOT:-$HOME/.local/share/agent-factory}"
BIN_DIR="${AGENT_FACTORY_BIN_DIR:-$HOME/.local/bin}"
RELEASE_BASE_URL="${AGENT_FACTORY_RELEASE_BASE_URL:-}"
PUBLIC_KEY_FILE="${AGENT_FACTORY_RELEASE_PUBLIC_KEY_FILE:-}"

command -v curl >/dev/null 2>&1 || { echo "error: curl is required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "error: OpenSSL is required" >&2; exit 1; }

case "$(uname -s)" in
  Darwin)
    platform="macos"
    extension="zip"
    command -v unzip >/dev/null 2>&1 || { echo "error: unzip is required" >&2; exit 1; }
    ;;
  Linux)
    platform="linux"
    extension="tar.gz"
    command -v tar >/dev/null 2>&1 || { echo "error: tar is required" >&2; exit 1; }
    ;;
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
elif [ -n "$RELEASE_BASE_URL" ]; then
  echo "error: AGENT_FACTORY_VERSION is required with AGENT_FACTORY_RELEASE_BASE_URL" >&2
  exit 1
else
  latest="$(curl --proto '=https' --tlsv1.2 -fsSL -o /dev/null -w '%{url_effective}' \
    "https://github.com/$REPOSITORY/releases/latest")"
  tag="${latest##*/}"
fi
[ -z "$PUBLIC_KEY_FILE" ] || [ -n "$RELEASE_BASE_URL" ] || {
  echo "error: a custom release key requires AGENT_FACTORY_RELEASE_BASE_URL" >&2
  exit 1
}

version="${tag#v}"
case "$version" in
  ""|*[!0-9A-Za-z.+-]*) echo "error: invalid release version" >&2; exit 1 ;;
  [0-9A-Za-z]*) ;;
  *) echo "error: invalid release version" >&2; exit 1 ;;
esac
asset="agent-factory-v${version}-${platform}-${architecture}.${extension}"
base="${RELEASE_BASE_URL:-https://github.com/$REPOSITORY/releases/download/$tag}"
temporary="$(mktemp -d "${TMPDIR:-/tmp}/agent-factory-install.XXXXXX")"
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

download() {
  url="$1"
  destination="$2"
  case "$url" in
    https://*) curl --proto '=https' --tlsv1.2 -fsSL "$url" -o "$destination" ;;
    *)
      [ -n "$RELEASE_BASE_URL" ] || { echo "error: refusing a non-HTTPS download" >&2; exit 1; }
      curl -fsSL "$url" -o "$destination"
      ;;
  esac
}

download "$base/$asset" "$temporary/$asset"
download "$base/SHA256SUMS" "$temporary/SHA256SUMS"
download "$base/SHA256SUMS.sig" "$temporary/SHA256SUMS.sig"

if [ -n "$PUBLIC_KEY_FILE" ]; then
  [ -f "$PUBLIC_KEY_FILE" ] || { echo "error: release public key not found" >&2; exit 1; }
  verification_key="$PUBLIC_KEY_FILE"
else
  verification_key="$temporary/RELEASE-SIGNING-KEY.pem"
  cat > "$verification_key" <<'PUBLIC_KEY'
-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAtmqCNJHM8Wuakgx9DCxk
+1xV68yaTcUijGWVkIdfY3OnosjdtfR5vXOLPmpR74Sg3k4QtNmRAW6SvjqU0u16
1YbN24lGElOjCg/Z6HT1sZigg3aUGCuFvNDBdA3UamYsk0OU5WgQc6PMeUWts1DD
+XIfOmZ3ogOJ0qUSgFMHaBc2z+A46hsmBiefUF76OaTU/q9DETtksj15zfaCPZAS
ivTnuQQNgkcEwxLd8cpr22wX0qIGJwCVA1CFTMkhnGBfi9BV6KB+j90xRLTaKD2k
nelv3KQFR/eh9Gs3MLeyXKW5RdXI5isqB1481wtEB7LAGItfBp/E3IfU0AX8rXsp
pd0FO3WakusoF5EkbLxbN9oarrDEJ0KJD1CDedLtp22AtiYkZtmzHrn/1Oe3TjbR
xELFWVekq1YErSw9D5SWll/QYIozhEHZnUP8UISa4tDkPIXNYDpsvcKpP37xvR3G
UQwkCso3EIBmZ9ZiZCRZFk4d1VZB2SkFRgLl8L9cTk/5AgMBAAE=
-----END PUBLIC KEY-----
PUBLIC_KEY
fi

openssl dgst -sha256 -verify "$verification_key" -signature "$temporary/SHA256SUMS.sig" \
  "$temporary/SHA256SUMS" >/dev/null 2>&1 || {
    echo "error: release signature verification failed" >&2
    exit 1
  }

expected="$(awk -v name="$asset" '$2 == name || $2 == "*" name {print $1}' \
  "$temporary/SHA256SUMS")"
[ -n "$expected" ] || { echo "error: release checksum is missing" >&2; exit 1; }

if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$temporary/$asset" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$temporary/$asset" | awk '{print $1}')"
fi
[ "$actual" = "$expected" ] || { echo "error: SHA-256 verification failed" >&2; exit 1; }

directory="agent-factory-v${version}-${platform}-${architecture}"
if [ "$extension" = "zip" ]; then
  unzip -Z1 "$temporary/$asset" | awk -v root="$directory/" '
    index($0, root) != 1 || $0 ~ /(^|\/)\.\.($|\/)/ { bad=1 }
    END { exit bad }
  ' || { echo "error: archive contains an unsafe path" >&2; exit 1; }
  unzip -q "$temporary/$asset" -d "$temporary/extracted"
else
  tar -tzf "$temporary/$asset" | awk -v root="$directory/" '
    $0 != substr(root, 1, length(root)-1) && index($0, root) != 1 { bad=1 }
    $0 ~ /(^|\/)\.\.($|\/)/ { bad=1 }
    END { exit bad }
  ' || { echo "error: archive contains an unsafe path" >&2; exit 1; }
  mkdir -p "$temporary/extracted"
  tar -xzf "$temporary/$asset" -C "$temporary/extracted"
fi

extracted="$temporary/extracted/$directory"
[ -x "$extracted/agent-factory" ] || { echo "error: archive is missing agent-factory" >&2; exit 1; }
"$extracted/agent-factory" self-test

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
target="$INSTALL_ROOT/$version"
if [ -e "$target" ]; then
  [ -x "$target/agent-factory" ] || { echo "error: existing install is invalid" >&2; exit 1; }
  "$target/agent-factory" self-test
  echo "Agent Factory $version is already installed; refreshing the command link"
else
  mv "$extracted" "$target"
fi
ln -sfn "$target/agent-factory" "$BIN_DIR/agent-factory"

echo "Agent Factory $version installed at $target"
if [ "${AGENT_FACTORY_NO_SETUP:-0}" = "1" ]; then
  echo "Ensure $BIN_DIR is in PATH, then run: agent-factory setup"
else
  echo "Opening local setup. Provider keys stay on this device."
  "$target/agent-factory" setup
fi
