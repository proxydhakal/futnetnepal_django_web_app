"""
Load `.env` via python-dotenv and read variables with small typed helpers.
Used by settings.py (and anywhere else that needs env before Django boots).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')


def env(key: str, default=None, *, required: bool = False) -> str:
    """Return a string env var (stripped). Empty string counts as unset."""
    raw = os.getenv(key)
    if raw is None or str(raw).strip() == '':
        if default is not None:
            return str(default)
        if required:
            raise RuntimeError(f'Missing required environment variable: {key}')
        return ''
    return str(raw).strip()


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None or str(raw).strip() == '':
        return default
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')


def env_int(key: str, default: int = 0) -> int:
    raw = os.getenv(key)
    if raw is None or str(raw).strip() == '':
        return default
    return int(str(raw).strip())


def env_csv(key: str, default: str = '') -> list[str]:
    raw = os.getenv(key)
    if raw is None or str(raw).strip() == '':
        raw = default
    return [item.strip() for item in str(raw).split(',') if item.strip()]
