"""Time-ordered UUIDs (UUIDv7) for primary keys."""

import os
import time
import uuid


def time_ordered_uuid():
    """UUIDv7 — sortable by creation time."""
    if hasattr(uuid, 'uuid7'):
        return uuid.uuid7()
    unix_ts_ms = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), 'big') & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), 'big') & ((1 << 62) - 1)
    uuid_int = (
        (unix_ts_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0x2 << 62)
        | rand_b
    )
    return uuid.UUID(int=uuid_int)
