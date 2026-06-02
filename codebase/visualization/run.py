#!/usr/bin/env python3
"""Small launcher for the RAG Challenge visualization app."""

from __future__ import annotations

import sys
from pathlib import Path

current_dir = Path(__file__).parent.resolve()
project_root = current_dir.parent.resolve()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(project_root))

from app import main  # noqa: E402


if __name__ == "__main__":
    main()
