"""Database privilege model (decision D-11, DR-2026-11-18-G4-8; doc 06 §22.6, doc 09 §19).

G4 enforces append-only behaviour with triggers, which hold for every role. Privileges add the
protections triggers can't give (TRUNCATE, executing maintenance functions, the maintenance
domain). Applying them to real roles is deployment work (deferred with AWS); this module is the
documented, tested source of the statements (``manage.py print_db_grants``).

Roles:
- **owner** (migration role): owns every object and runs migrations. Maintenance jobs (the TR-24
  protocol: partition create/drop, hold release, key rotation) run as this role, because
  partition DDL requires ownership. No business traffic uses it.
- **application**: the web and worker role. Full DML on ordinary tables; on logs only SELECT and
  INSERT; hold tables read-only (plus adding hold links); no access to maintenance tables and no
  EXECUTE on the SECURITY DEFINER maintenance functions.
"""

# Logs: append-only. The application may read and insert, never update/delete/truncate.
APPEND_ONLY_LOGS = ("account_security_event", "audit_log")
# Hold tables: rows are removed only by the SECURITY DEFINER maintenance functions.
HOLD_TABLES_READ = ("audit_log_hold", "audit_log_all")
HOLD_LINK_INSERT = ("audit_log_hold_link",)
# The maintenance domain (doc 09 §19.2: no business transaction touches these tables).
MAINTENANCE_TABLES = (
    "maintenance_operation",
    "registry_stream_head",
    "maintenance_audit_log",
    "maintenance_approval",
    "shredded_pseudonym",
    "kek_rewrap_log",
)
MAINTENANCE_FUNCTIONS = (
    "release_held_events(uuid)",
    "archive_and_drop_audit_partition(regclass, timestamptz)",
    "ensure_uuid7_partitions(regclass, text, integer)",
)


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError("role and schema names must be simple identifiers")
    return name


def application_grants(app_role: str, schema: str = "public") -> list[str]:
    role, sch = _ident(app_role), _ident(schema)
    statements = [
        f"REVOKE ALL ON ALL TABLES IN SCHEMA {sch} FROM {role}",
        f"GRANT USAGE ON SCHEMA {sch} TO {role}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {sch} TO {role}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {sch} TO {role}",
    ]
    for table in APPEND_ONLY_LOGS + HOLD_TABLES_READ + HOLD_LINK_INSERT + MAINTENANCE_TABLES:
        statements.append(f"REVOKE ALL ON {sch}.{table} FROM {role}")
    for table in APPEND_ONLY_LOGS:
        statements.append(f"GRANT SELECT, INSERT ON {sch}.{table} TO {role}")
    for table in HOLD_TABLES_READ:
        statements.append(f"GRANT SELECT ON {sch}.{table} TO {role}")
    for table in HOLD_LINK_INSERT:
        statements.append(f"GRANT SELECT, INSERT ON {sch}.{table} TO {role}")
    for function in MAINTENANCE_FUNCTIONS:
        statements.append(f"REVOKE ALL ON FUNCTION {sch}.{function} FROM PUBLIC, {role}")
    return statements
