"""Fail-safe test-database target check (KI-38).

The test settings refuse to load unless ``DATABASE_URL`` is set explicitly and points to an
approved disposable PostgreSQL server: a loopback host on an allowed port (by default the
disposable containers on 55432 and 55418; ``TEST_DATABASE_ALLOWED_PORTS`` may change the list).
Port 5432 is always refused, because a server there may be the developer's own PostgreSQL; a
missing port (libpq would use 5432) and Unix sockets are refused for the same reason. Nothing is
substituted: a refused configuration stops before any connection is attempted. Messages name
the variable and the rule, never the URL (it may hold a password).
"""

from collections.abc import Mapping
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

DEFAULT_ALLOWED_PORTS = "55432,55418"
FORBIDDEN_PORTS = frozenset({5432})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
POSTGRES_SCHEMES = frozenset({"postgres", "postgresql", "pgsql", "postgis"})


def allowed_ports(environ: Mapping) -> frozenset[int]:
    raw = environ.get("TEST_DATABASE_ALLOWED_PORTS") or DEFAULT_ALLOWED_PORTS
    try:
        ports = frozenset(int(p) for p in raw.split(",") if p.strip())
    except ValueError:
        raise ImproperlyConfigured(
            "TEST_DATABASE_ALLOWED_PORTS must be a comma-separated list of ports."
        ) from None
    return ports - FORBIDDEN_PORTS


def target_errors(name: str, url: str | None, environ: Mapping) -> list[str]:
    """Problems with one test-database URL (an empty list means it is acceptable)."""
    if not url:
        return [
            f"{name} must be set explicitly for tests (a disposable PostgreSQL database, "
            "for example the container on 127.0.0.1:55432); there is no default."
        ]
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return [f"{name} is not a valid database URL."]
    if parts.scheme not in POSTGRES_SCHEMES:
        return [f"{name} must point to PostgreSQL (TR-13)."]
    host = (parts.hostname or "").lower()
    if not host or host.startswith("/") or "%2f" in (parts.netloc or "").lower():
        return [f"{name} must name a loopback host and port; Unix sockets are refused."]
    errors = []
    if host not in LOOPBACK_HOSTS:
        errors.append(f"{name} must point to a local disposable server (loopback host only).")
    if port is None:
        errors.append(f"{name} must give the port explicitly (without one, PostgreSQL uses 5432).")
    elif port in FORBIDDEN_PORTS:
        errors.append(
            f"{name} must not use port 5432: it may be the developer's own PostgreSQL server."
        )
    elif port not in allowed_ports(environ):
        errors.append(
            f"{name} uses a port outside the approved disposable test ports "
            "(TEST_DATABASE_ALLOWED_PORTS)."
        )
    return errors


def require_disposable_test_database(environ: Mapping) -> None:
    """Called by ``config.settings.test`` at import time."""
    errors = target_errors("DATABASE_URL", environ.get("DATABASE_URL"), environ)
    extra = environ.get("MATERMONIAL_TEST_POSTGRES_URL")
    if extra:
        errors += target_errors("MATERMONIAL_TEST_POSTGRES_URL", extra, environ)
    if errors:
        raise ImproperlyConfigured("Refusing to load test settings (KI-38): " + " ".join(errors))
