#!/usr/bin/env python3
"""Run the local nxnative checkout with this Mac's toolchain and a temporary keyset.

The supplied key file is never changed. A few malformed source entries in the
current file are omitted only from a private temporary copy, removed at exit.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", required=True, type=Path)
    ap.add_argument("--game-dir", required=True, type=Path)
    ap.add_argument("--platform", choices=("mac", "mac-app", "ios"), default="mac")
    ap.add_argument("--language", default="ja")
    ap.add_argument("--survey-only", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    source = args.keys.resolve()
    if not source.is_file():
        ap.error(f"key file not found: {source}")
    kept = []
    omitted = 0
    for line in source.read_text().splitlines():
        if "=" in line:
            name, value = map(str.strip, line.split("=", 1))
            if name.startswith(("master_kek_source_", "mariko_master_kek_source_")) and len(value) != 32:
                omitted += 1
                continue
        kept.append(line)

    fd, temporary = tempfile.mkstemp(prefix="tgaa-key-build-", suffix=".keys")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write("\n".join(kept) + "\n")
        env = os.environ.copy()
        env.update(
            DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",
            TOOLCHAINS="com.apple.dt.toolchain.Metal.32023.921.5",
            DOTNET_ROOT="/opt/homebrew/opt/dotnet/libexec",
            DOTNET_CLI_HOME=str(ROOT / "local-data/dotnet"),
            NUGET_PACKAGES=str(ROOT / "local-data/nuget"),
            SSL_CERT_FILE="/etc/ssl/cert.pem",
            PATH=str(ROOT / "local-data/venv/bin") + os.pathsep + env.get("PATH", ""),
        )
        cmd = [
            sys.executable,
            str(ROOT / "upstream/nxnative/scripts/build_ipa_from_nsp.py"),
            str(args.game_dir.resolve()),
            "-k",
            temporary,
            "--platform",
            "ios" if args.survey_only else args.platform,
            "--language",
            args.language,
            "--progress",
            "lines",
        ]
        if args.survey_only:
            cmd.append("--survey-only")
        if args.out:
            cmd += ["--out", str(args.out.resolve())]
        print(f"Temporary keyset: {len(kept)} lines retained, {omitted} malformed source entries omitted; removed at exit.", flush=True)
        return subprocess.call(cmd, env=env, cwd=ROOT / "upstream/nxnative")
    finally:
        os.unlink(temporary)


if __name__ == "__main__":
    raise SystemExit(main())
