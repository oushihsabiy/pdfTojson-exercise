#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append a timestamped entry to CHANGE_LOG.md.

Usage:
  python scripts/record_change.py "Short description of change"

If invoked without arguments, opens an editor to compose the entry body.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    changelog = Path.cwd() / "CHANGE_LOG.md"
    if not changelog.exists():
        changelog.write_text("", encoding="utf-8")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if len(sys.argv) >= 2:
        msg = sys.argv[1]
    else:
        # fallback: read from stdin
        try:
            msg = sys.stdin.read().strip()
        except Exception:
            msg = ""

    if not msg:
        print("Usage: scripts/record_change.py \"Short description\"")
        return 2

    entry = f"{now}  — {msg}\n\n"
    with changelog.open("a", encoding="utf-8") as f:
        f.write(entry)

    print(f"Appended to {changelog}: {msg}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
