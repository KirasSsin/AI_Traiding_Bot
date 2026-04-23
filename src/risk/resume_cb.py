"""CLI: python -m src.risk.resume_cb --level {L2,L3,FLASH} --reason "..." [--expires-in 1h]"""

import argparse
import re
from datetime import UTC, datetime, timedelta

from src.platform.config import Settings
from src.risk.override import CbOverride, OverrideStore

_DURATION_RE = re.compile(r"^(\d+)([hmd])$")


def parse_duration(s: str) -> timedelta:
    m = _DURATION_RE.match(s)
    if not m:
        raise argparse.ArgumentTypeError(f"invalid duration: {s} (expected NNh|NNm|NNd)")
    n, unit = int(m.group(1)), m.group(2)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "m":
        return timedelta(minutes=n)
    return timedelta(days=n)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.risk.resume_cb")
    parser.add_argument("--level", required=True, choices=["L2", "L3", "FLASH"])
    parser.add_argument("--reason", required=True, type=str)
    parser.add_argument("--expires-in", default="1h", type=parse_duration)
    args = parser.parse_args(argv)

    settings = Settings()  # type: ignore[call-arg]
    now = datetime.now(UTC)
    override = CbOverride(
        level=args.level,
        reason=args.reason,
        config_hash=settings.config_hash(),
        created_at=now,
        expires_at=now + args.expires_in,
    )
    store = OverrideStore(settings.risk_override_path)
    store.write(override=override)
    print(f"Override written: {settings.risk_override_path}")
    print(f"Level={args.level} expires_at={override.expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
