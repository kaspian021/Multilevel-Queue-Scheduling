#!/usr/bin/env python3
"""Copy the canonical simulation core into every exercise folder.

Each exercise branch is flat and self-contained, so ``lst_core.py`` is
duplicated into ``exercise-N/code/``.  Copying by hand is how two copies drift
apart, so this script does it: run it after any change to ``core/lst_core.py``
and the exercises all move together.

    python3 tools/vendor_core.py            # copy
    python3 tools/vendor_core.py --check    # fail if any copy is out of date
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CORE = os.path.join(REPO, "core", "lst_core.py")
EXERCISES = [f"exercise-{n}" for n in range(1, 8)]


def exercises(root: str) -> list:
    return [d for d in sorted(os.listdir(root))
            if d.startswith("exercise-") and
            os.path.isdir(os.path.join(root, d, "code"))]


def digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report drift instead of copying")
    args = ap.parse_args(argv)

    if not os.path.exists(CORE):
        print(f"canonical core not found: {CORE}", file=sys.stderr)
        return 1
    want = digest(CORE)

    targets = [os.path.join(REPO, e, "code", "lst_core.py")
               for e in exercises(REPO)]
    missing = [e for e in EXERCISES
               if not os.path.isdir(os.path.join(REPO, e, "code"))]

    if args.check:
        bad = [t for t in targets
               if not os.path.exists(t) or digest(t) != want]
        for t in bad:
            print(f"  out of date: {os.path.relpath(t, REPO)}")
        for e in missing:
            print(f"  no code/ folder: {e}")
        if bad or missing:
            print("run tools/vendor_core.py")
            return 1
        print(f"all {len(targets)} copies match the canonical core")
        return 0

    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copyfile(CORE, t)
    for e in missing:
        os.makedirs(os.path.join(REPO, e, "code"), exist_ok=True)
        shutil.copyfile(CORE, os.path.join(REPO, e, "code", "lst_core.py"))
    print(f"vendored core -> {len(targets) + len(missing)} exercise folders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
