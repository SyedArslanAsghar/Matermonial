"""Project-wide SQL for partitioned, append-only logs (TR-23; doc 03 §22.15, doc 06 §22.6).

Migrations embed frozen copies of these strings; keep them in sync when changing either.

- ``ensure_uuid7_partitions(parent, step, ahead)``: creates the current and the next ``ahead``
  month (or year) RANGE partitions of a UUIDv7-keyed table, bounded with ``uuid_v7_lower``.
  Only current and future ranges are created: past ranges are never re-created.
- ``reject_row_change()``: append-only trigger (UPDATE/DELETE rejected for every role; whole
  partitions are dropped at end of retention by the maintenance role, doc 09).
- ``check_enc_parts()``: envelope array well-formed, one envelope per pseudonym.
"""

LOG_SQL_FUNCTIONS = """
CREATE FUNCTION ensure_uuid7_partitions(parent regclass, step text, ahead integer)
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE
  base   timestamp;
  lo     timestamp;
  hi     timestamp;
  pname  text;
  made   integer := 0;
BEGIN
  IF step NOT IN ('month', 'year') THEN
    RAISE EXCEPTION 'step must be month or year';
  END IF;
  base := date_trunc(step, now() AT TIME ZONE 'UTC');
  FOR i IN 0..ahead LOOP
    lo := base + CASE step WHEN 'month' THEN make_interval(months => i)
                           ELSE make_interval(years => i) END;
    hi := lo + CASE step WHEN 'month' THEN interval '1 month' ELSE interval '1 year' END;
    pname := parent::text || '_' ||
             to_char(lo, CASE step WHEN 'month' THEN 'YYYY_MM' ELSE 'YYYY' END);
    IF to_regclass(pname) IS NULL THEN
      EXECUTE format('CREATE TABLE %I PARTITION OF %s FOR VALUES FROM (%L) TO (%L)',
                     pname, parent, uuid_v7_lower(lo AT TIME ZONE 'UTC'),
                     uuid_v7_lower(hi AT TIME ZONE 'UTC'));
      made := made + 1;
    END IF;
  END LOOP;
  RETURN made;
END $$;

CREATE FUNCTION reject_row_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '%: append-only, % rejected', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'insufficient_privilege';
END $$;

CREATE FUNCTION check_enc_parts() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF jsonb_typeof(NEW.enc_parts) <> 'array' THEN
    RAISE EXCEPTION 'enc_parts must be a JSON array' USING ERRCODE = 'check_violation';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.enc_parts) e
             WHERE jsonb_typeof(e) <> 'object'
                OR NOT (e ?& ARRAY['pseudonym', 'key_id', 'kek_version', 'nonce', 'ciphertext'])) THEN
    RAISE EXCEPTION 'enc_parts: malformed envelope' USING ERRCODE = 'check_violation';
  END IF;
  IF (SELECT count(*) FROM jsonb_array_elements(NEW.enc_parts))
     <> (SELECT count(DISTINCT e->>'pseudonym') FROM jsonb_array_elements(NEW.enc_parts) e) THEN
    RAISE EXCEPTION 'enc_parts: one envelope per pseudonym' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
"""

LOG_SQL_FUNCTIONS_REVERSE = """
DROP FUNCTION IF EXISTS check_enc_parts();
DROP FUNCTION IF EXISTS reject_row_change();
DROP FUNCTION IF EXISTS ensure_uuid7_partitions(regclass, text, integer);
"""

# Partitions are created this many periods ahead (doc 03 §22.15: "3 months ahead").
PARTITIONS_AHEAD = 3
