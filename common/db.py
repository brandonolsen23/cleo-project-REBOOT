import os
import time
import socket
from typing import Optional

import psycopg2
from psycopg2 import OperationalError


def _ensure_sslmode(url: str) -> str:
    if "sslmode=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}sslmode=require"

def _with_port(dsn: str, port: str) -> str:
    if ":5432/" in dsn or ":6543/" in dsn:
        dsn = dsn.replace(":5432/", f":{port}/").replace(":6543/", f":{port}/")
    return dsn


def connect_with_retries(
    url: Optional[str] = None,
    attempts: int = 5,
    backoff_sec: float = 2.0,
    prefer_pooler: bool = True,
):
    """Connect to Postgres with retries, preferring PgBouncer (6543) first.

    - Ensures sslmode=require in DSN.
    - Tries the preferred port with retries, then falls back to the other port.
    - By default prefers pooled port 6543 for reliability.
    """
    base = _ensure_sslmode(url or os.getenv("DATABASE_URL", ""))
    if not base:
        raise RuntimeError("DATABASE_URL is not set")

    # Try to prefer IPv4 by adding hostaddr if missing, to avoid environments
    # that can't reach IPv6. Leave as-is if resolution fails or hostaddr exists.
    if "hostaddr=" not in base:
        try:
            # crude parse: extract hostname between '//' and next ':' or '/'
            host = base.split("//", 1)[1].split("@", 1)[-1]
            host = host.split(":", 1)[0].split("/", 1)[0]
            infos = socket.getaddrinfo(host, None, family=socket.AF_INET)
            if infos:
                ipv4 = infos[0][4][0]
                sep = "&" if "?" in base else "?"
                base = f"{base}{sep}hostaddr={ipv4}"
        except Exception:
            pass

    primary_port = "6543" if prefer_pooler else "5432"
    secondary_port = "5432" if prefer_pooler else "6543"

    for port in (primary_port, secondary_port):
        dsn = _with_port(base, port)
        last_err = None
        for i in range(attempts):
            try:
                return psycopg2.connect(dsn)
            except OperationalError as e:
                last_err = e
                time.sleep(backoff_sec * (i + 1))
        # try next port
    # if we reached here, both ports failed
    raise last_err  # type: ignore[name-defined]
