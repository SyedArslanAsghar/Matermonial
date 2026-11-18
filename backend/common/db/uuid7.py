"""UUIDv7 support (TR-23; doc 03 §22.15, baseline v4.6 §4).

Database side: migrations create ``uuid_v7()`` (the native ``uuidv7()`` on PostgreSQL 18, the
RFC 9562 body on 16) and ``uuid_v7_lower(ts)``. Tables use ``uuid_v7()`` as the column default.

Python side: some identifiers must exist before the row is inserted (for example
``maintenance_audit_log.log_row_id``, generated before sequence allocation, and ``op_id``).
Python 3.12/3.13 have no ``uuid.uuid7``, so this module implements the same RFC 9562 layout:
48-bit Unix millisecond timestamp, version 7, 12-bit ``rand_a``, variant ``10``, 62-bit
``rand_b``.
"""

import os
import time
import uuid
from datetime import datetime

from django.db import models

V7_SQL_FUNCTIONS = """
DO $outer$
BEGIN
  IF current_setting('server_version_num')::int >= 180000 THEN
    -- PostgreSQL 18: wrap the built-in generator (baseline v4.6 §4.1).
    EXECUTE $f$
      CREATE OR REPLACE FUNCTION uuid_v7() RETURNS uuid
      LANGUAGE sql VOLATILE PARALLEL SAFE AS 'SELECT uuidv7()'
    $f$;
  ELSE
    -- PostgreSQL 15/16: RFC 9562 layout; gen_random_uuid() is built in from 13.
    EXECUTE $f$
      CREATE OR REPLACE FUNCTION uuid_v7() RETURNS uuid
      LANGUAGE plpgsql VOLATILE PARALLEL SAFE AS $body$
      DECLARE
        ts_ms bigint := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;
        b     bytea  := uuid_send(gen_random_uuid());
      BEGIN
        b := overlay(b PLACING substring(int8send(ts_ms) FROM 3 FOR 6) FROM 1 FOR 6);
        b := set_byte(b, 6, (get_byte(b, 6) & 15) | 112);
        b := set_byte(b, 8, (get_byte(b, 8) & 63) | 128);
        RETURN encode(b, 'hex')::uuid;
      END $body$
    $f$;
  END IF;
END $outer$;

-- Smallest valid UUIDv7 for the millisecond containing ts (baseline v4.6 §4.2).
CREATE OR REPLACE FUNCTION uuid_v7_lower(ts timestamptz) RETURNS uuid
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
  SELECT encode(
           substring(int8send(floor(extract(epoch FROM ts) * 1000)::bigint) FROM 3 FOR 6)
           || '\\x70008000000000000000'::bytea,
         'hex')::uuid
$$;
"""

V7_SQL_FUNCTIONS_REVERSE = """
DROP FUNCTION IF EXISTS uuid_v7_lower(timestamptz);
DROP FUNCTION IF EXISTS uuid_v7();
"""


def uuid7(ms: int | None = None) -> uuid.UUID:
    """A random UUIDv7 for the given Unix millisecond timestamp (default: now)."""
    if ms is None:
        ms = time.time_ns() // 1_000_000
    if not 0 <= ms < 1 << 48:
        raise ValueError("timestamp out of UUIDv7 range")
    raw = bytearray(ms.to_bytes(6, "big") + os.urandom(10))
    raw[6] = (raw[6] & 0x0F) | 0x70  # version 7
    raw[8] = (raw[8] & 0x3F) | 0x80  # variant 10
    return uuid.UUID(bytes=bytes(raw))


def uuid7_lower(moment: datetime) -> uuid.UUID:
    """Python twin of uuid_v7_lower(): smallest UUIDv7 in moment's millisecond."""
    if moment.tzinfo is None:
        raise ValueError("moment must be timezone-aware")
    ms = int(moment.timestamp() * 1000)
    return uuid.UUID(bytes=ms.to_bytes(6, "big") + bytes.fromhex("70008000000000000000"))


def uuid7_timestamp_ms(value: uuid.UUID) -> int:
    return int.from_bytes(value.bytes[:6], "big")


def is_uuid7(value: uuid.UUID) -> bool:
    return value.version == 7 and value.variant == uuid.RFC_4122


class UUIDv7Default(models.Func):
    """Database default ``uuid_v7()`` for UUIDv7 primary keys (use with ``db_default``)."""

    function = "uuid_v7"
    template = "%(function)s()"
    output_field = models.UUIDField()
