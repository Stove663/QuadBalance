"""Filesystem helpers for workbench runs and SQLite storage."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import secrets


DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_NAME = "quadbalance.db"
DEFAULT_OUTPUT_ROOT = Path("output")


def default_db_path(data_dir: Path | None = None) -> Path:
    root = data_dir if data_dir is not None else DEFAULT_DATA_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root / DEFAULT_DB_NAME


def allocate_run_dir(output_root: Path | None = None) -> Path:
    """Create a unique output/<run_id>/ directory for a workbench run."""
    root = output_root if output_root is not None else DEFAULT_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stamp}_{secrets.token_hex(3)}"
    path = root / run_id
    path.mkdir(parents=True, exist_ok=False)
    return path
