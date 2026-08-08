from __future__ import annotations

import base64
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    public_key = (ROOT / "RELEASE-SIGNING-KEY.pem").read_text(encoding="ascii")
    shell_installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    powershell_installer = (ROOT / "install.ps1").read_text(encoding="utf-8")
    if public_key.strip() not in shell_installer:
        raise SystemExit("install.sh does not pin RELEASE-SIGNING-KEY.pem")

    match = re.search(r'\$PinnedModulus = "([A-Za-z0-9+/=]+)"', powershell_installer)
    if match is None:
        raise SystemExit("install.ps1 has no pinned RSA modulus")
    pinned_modulus = base64.b64decode(match.group(1), validate=True)
    result = subprocess.run(
        [
            "openssl",
            "rsa",
            "-pubin",
            "-in",
            str(ROOT / "RELEASE-SIGNING-KEY.pem"),
            "-modulus",
            "-noout",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    expected_modulus = bytes.fromhex(result.stdout.strip().removeprefix("Modulus="))
    if pinned_modulus != expected_modulus:
        raise SystemExit("install.ps1 pins a different release key")


if __name__ == "__main__":
    main()
