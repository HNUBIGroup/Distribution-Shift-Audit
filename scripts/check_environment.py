#!/usr/bin/env python
"""Check the runtime environment.

Usage:
  python scripts/check_environment.py
  python scripts/check_environment.py --warn-only
"""

from __future__ import annotations

import argparse
import importlib
import platform
import sys


REQUIRED = [
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "matplotlib",
    "seaborn",
    "openpyxl",
    "torch",
]

OPTIONAL = [
    "torch_geometric",
    "rdkit",
    "transformers",
    "dgl",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-only", action="store_true", help="Report missing required packages but exit with status 0.")
    return parser.parse_args()


def module_version(name: str) -> str:
    module = importlib.import_module(name)
    return str(getattr(module, "__version__", "version_unknown"))


def main() -> int:
    args = parse_args()
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Platform: {platform.platform()}")

    ok = True
    for name in REQUIRED:
        try:
            print(f"OK required {name}: {module_version(name)}")
        except Exception as exc:
            ok = False
            print(f"MISSING required {name}: {exc}")

    for name in OPTIONAL:
        try:
            print(f"OK optional {name}: {module_version(name)}")
        except Exception as exc:
            print(f"WARN optional {name}: {exc}")

    try:
        import torch

        print(f"Torch CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"Torch CUDA device count: {torch.cuda.device_count()}")
            print(f"Torch CUDA device 0: {torch.cuda.get_device_name(0)}")
    except Exception as exc:
        ok = False
        print(f"ERROR checking torch CUDA: {exc}")

    if not ok and args.warn_only:
        print("WARN environment check had required-package issues, but --warn-only was set.")
        return 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
