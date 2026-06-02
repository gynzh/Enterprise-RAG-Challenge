from __future__ import annotations

import importlib
import sys
from pathlib import Path


CHECKS = [
    ("click", "click"),
    ("pyprojroot", "pyprojroot"),
    ("pandas", "pandas"),
    ("docling", "docling"),
    ("faiss", "faiss-cpu"),
    ("langchain", "langchain"),
    ("sentence_transformers", "sentence-transformers"),
    ("gradio", "gradio; install with `uv sync --group viz` or `uv sync --all-groups`"),
]


def main() -> int:
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Working directory: {Path.cwd()}")
    print()

    failed = []
    for module_name, package_hint in CHECKS:
        try:
            importlib.import_module(module_name)
            print(f"[OK] {module_name}")
        except Exception as exc:  # noqa: BLE001 - diagnostic script
            print(f"[MISSING] {module_name}  ({package_hint}) -> {exc}")
            failed.append(module_name)

    if failed:
        print()
        print("Some imports failed. Run one of:")
        print("  uv sync")
        print("  uv sync --all-groups")
        return 1

    print()
    print("Environment looks good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
