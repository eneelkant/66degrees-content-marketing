"""CLI entrypoint for approved reference library refresh."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure repository root is importable when invoked as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh approved 66degrees reference sources.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the 2-day staleness gate and refresh immediately.",
    )
    args = parser.parse_args(argv)
    force = args.force or os.getenv("FORCE_REFERENCE_REFRESH", "").lower() in {"1", "true", "yes"}

    from core.mcp_legacy.tools import refresh_reference_library

    try:
        result = refresh_reference_library(force=force)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        payload = {
            "status": "FAILED",
            "error": str(exc),
            "hint": (
                "Check network access to approved sources, Playwright Chromium install, "
                "and that no secrets are required for public pages."
            ),
        }
        print(json.dumps(payload, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in {"CURRENT", "REFRESHED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
