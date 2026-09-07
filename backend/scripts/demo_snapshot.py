"""Freeze / restore the demo-critical tables so a live presentation never
depends on the FIRMS API or a fresh clustering run.

    python scripts/demo_snapshot.py dump      # DB  -> data/demo/*.jsonl
    python scripts/demo_snapshot.py load      # files -> DB (truncate + insert)

Dumps `thermal_source`, `classification`, `osm_infra`, `flare_ref` — enough
for every endpoint and both frontends to work. `detection` (647k rows) is
skipped; it is only needed to re-run clustering, which the demo does not do.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.core.db import engine

OUT = Path(__file__).resolve().parents[2] / "data" / "demo"
TABLES = ["thermal_source", "classification", "osm_infra", "flare_ref"]
# geometry columns are read/written as EWKT so the file is portable
GEOM_COLS = {"thermal_source": ["geom"], "osm_infra": ["geom"], "flare_ref": ["geom"]}


def dump() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with engine.connect() as c:
        for t in TABLES:
            geoms = GEOM_COLS.get(t, [])
            cols = [r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=:t ORDER BY ordinal_position"), {"t": t})]
            sel = ", ".join(
                f"ST_AsEWKT({col}) AS {col}" if col in geoms else col for col in cols
            )
            rows = c.execute(text(f"SELECT {sel} FROM {t}")).mappings().all()
            path = OUT / f"{t}.jsonl"
            with path.open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps({k: _ser(v) for k, v in row.items()}) + "\n")
            print(f"  {t}: {len(rows)} rows -> {path.name}")


def load() -> None:
    with engine.begin() as c:
        for t in reversed(TABLES):
            c.execute(text(f"TRUNCATE {t} RESTART IDENTITY CASCADE"))
        for t in TABLES:
            path = OUT / f"{t}.jsonl"
            if not path.exists():
                print(f"  {t}: no dump file, skipped")
                continue
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            if not rows:
                continue
            for r in rows:  # JSON/JSONB columns: hand psycopg2 a string, not a dict
                for k, v in r.items():
                    if isinstance(v, (dict, list)):
                        r[k] = json.dumps(v)
            cols = list(rows[0])
            placeholders = ", ".join(
                f"ST_GeomFromEWKT(:{col})" if col in GEOM_COLS.get(t, []) else f":{col}"
                for col in cols
            )
            c.execute(text(f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({placeholders})"), rows)
            print(f"  {t}: {len(rows)} rows restored")


def _ser(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump":
        dump()
    elif cmd == "load":
        load()
    else:
        sys.exit("usage: demo_snapshot.py [dump|load]")
