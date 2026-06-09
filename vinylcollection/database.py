"""SQLite backend for the Vinyl Collection Dashboard."""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def _app_root() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


DEFAULT_DB_PATH = _app_root() / "vinyl.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vinyls (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    release_id       TEXT UNIQUE,
    title            TEXT NOT NULL DEFAULT '',
    artist           TEXT DEFAULT '',
    year             INTEGER DEFAULT 0,
    label            TEXT DEFAULT '',
    catno            TEXT DEFAULT '',
    format           TEXT DEFAULT '',
    country          TEXT DEFAULT '',
    genre            TEXT DEFAULT '',
    style            TEXT DEFAULT '',
    condition        TEXT DEFAULT '',
    purchase_price   REAL,
    purchase_date    TEXT DEFAULT '',
    discogs_url      TEXT DEFAULT '',
    cover_image_url  TEXT DEFAULT '',
    lowest_price     REAL,
    price_currency   TEXT DEFAULT 'EUR',
    num_for_sale     INTEGER DEFAULT 0,
    tracklist_count  INTEGER DEFAULT 0,
    notes            TEXT DEFAULT '',
    condition_prices TEXT DEFAULT NULL,
    tags             TEXT DEFAULT '',
    purchase_location TEXT DEFAULT '',
    added_date       TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS wantlist (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    release_id       TEXT UNIQUE,
    title            TEXT NOT NULL DEFAULT '',
    artist           TEXT DEFAULT '',
    year             INTEGER DEFAULT 0,
    label            TEXT DEFAULT '',
    catno            TEXT DEFAULT '',
    format           TEXT DEFAULT '',
    country          TEXT DEFAULT '',
    genre            TEXT DEFAULT '',
    style            TEXT DEFAULT '',
    cover_image_url  TEXT DEFAULT '',
    discogs_url      TEXT DEFAULT '',
    lowest_price     REAL,
    price_currency   TEXT DEFAULT 'EUR',
    num_for_sale     INTEGER DEFAULT 0,
    tracklist_count  INTEGER DEFAULT 0,
    notes            TEXT DEFAULT '',
    max_price        REAL,
    condition        TEXT DEFAULT '',
    added_date       TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS price_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    release_id  TEXT NOT NULL,
    snap_date   TEXT DEFAULT (date('now')),
    lowest_price REAL,
    condition_prices TEXT,
    UNIQUE(release_id, snap_date)
);
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """Apply incremental DB migrations (safe to run on existing DBs)."""
        for sql in [
            "ALTER TABLE vinyls ADD COLUMN condition_prices TEXT",
            "ALTER TABLE vinyls ADD COLUMN tags TEXT DEFAULT ''",
            "ALTER TABLE vinyls ADD COLUMN purchase_location TEXT DEFAULT ''",
        ]:
            try:
                self.conn.execute(sql)
                self.conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

    # ------------------------------------------------------------------
    # Price history
    # ------------------------------------------------------------------

    def add_price_snapshot(self, release_id: str, lowest_price: float | None,
                           condition_prices: str | None = None) -> None:
        """Record today's price snapshot (one per release per day)."""
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO price_history (release_id, snap_date, lowest_price, condition_prices) "
                "VALUES (?, date('now'), ?, ?)",
                (release_id, lowest_price, condition_prices),
            )
            self.conn.commit()
        except Exception:
            pass

    def get_price_history(self, release_id: str | None = None, limit: int = 90) -> list[dict]:
        """Return price snapshots.  If release_id is None, return aggregate daily totals."""
        if release_id:
            rows = self.conn.execute(
                "SELECT snap_date, lowest_price, condition_prices FROM price_history "
                "WHERE release_id = ? ORDER BY snap_date DESC LIMIT ?",
                (release_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT snap_date, SUM(lowest_price) AS lowest_price, NULL AS condition_prices "
                "FROM price_history GROUP BY snap_date ORDER BY snap_date DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_vinyl(self, **fields) -> int:
        fields.pop("id", None)
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        cur = self.conn.execute(
            f"INSERT INTO vinyls ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_vinyl(self, vinyl_id: int, **fields) -> None:
        fields.pop("id", None)
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [vinyl_id]
        self.conn.execute(f"UPDATE vinyls SET {sets} WHERE id = ?", vals)
        self.conn.commit()

    def delete_vinyl(self, vinyl_id: int) -> None:
        self.conn.execute("DELETE FROM vinyls WHERE id = ?", (vinyl_id,))
        self.conn.commit()

    def get_vinyl(self, vinyl_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM vinyls WHERE id = ?", (vinyl_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_vinyl_by_release_id(self, release_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM vinyls WHERE release_id = ?", (release_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_vinyls(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM vinyls ORDER BY artist COLLATE NOCASE, title COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM vinyls").fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Wantlist
    # ------------------------------------------------------------------

    def add_want(self, **fields) -> int:
        fields.pop("id", None)
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        cur = self.conn.execute(
            f"INSERT INTO wantlist ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_want(self, want_id: int, **fields) -> None:
        fields.pop("id", None)
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [want_id]
        self.conn.execute(f"UPDATE wantlist SET {sets} WHERE id = ?", vals)
        self.conn.commit()

    def delete_want(self, want_id: int) -> None:
        self.conn.execute("DELETE FROM wantlist WHERE id = ?", (want_id,))
        self.conn.commit()

    def get_all_wants(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM wantlist ORDER BY artist COLLATE NOCASE, title COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_want_by_release_id(self, release_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM wantlist WHERE release_id = ?", (release_id,)
        ).fetchone()
        return dict(row) if row else None

    def move_want_to_collection(self, want_id: int, **extra_fields) -> int:
        """Move a wantlist entry into the collection and remove from wantlist."""
        row = self.conn.execute("SELECT * FROM wantlist WHERE id = ?", (want_id,)).fetchone()
        if not row:
            raise ValueError(f"Want {want_id} not found")
        data = dict(row)
        data.pop("id", None)
        data.pop("max_price", None)
        data.update(extra_fields)
        # Remove fields not in vinyls
        allowed = {
            "release_id", "title", "artist", "year", "label", "format", "genre",
            "cover_image_url", "discogs_url", "lowest_price", "price_currency",
            "num_for_sale", "notes", "condition", "purchase_price", "purchase_date",
            "catno", "country", "style", "tracklist_count", "tags", "purchase_location",
        }
        data = {k: v for k, v in data.items() if k in allowed}
        new_id = self.add_vinyl(**data)
        self.delete_want(want_id)
        return new_id

    def get_stats(self) -> dict:
        all_v = self.get_all_vinyls()
        total = len(all_v)
        artists = len(set(v.get("artist", "").lower() for v in all_v if v.get("artist")))
        total_cost = sum(v.get("purchase_price") or 0 for v in all_v)
        total_market = sum(v.get("lowest_price") or 0 for v in all_v)
        wants = self.conn.execute("SELECT COUNT(*) FROM wantlist").fetchone()[0]
        currency = self.get_config("currency", "EUR")
        db_path = str(self.db_path)

        # Breakdown helpers
        def count_map(key, split=False):
            m: dict = {}
            for v in all_v:
                raw = (v.get(key) or "").strip()
                tags = [t.strip() for t in raw.split(",") if t.strip()] if split and raw else ([raw] if raw else ["Unknown"])
                for tag in tags:
                    m[tag] = m.get(tag, 0) + 1
            return dict(sorted(m.items(), key=lambda x: -x[1]))

        by_genre = count_map("genre", split=True)
        by_condition = count_map("condition")
        by_format = {}
        for v in all_v:
            f = ((v.get("format") or "").split(",")[0]).strip() or "Unknown"
            by_format[f] = by_format.get(f, 0) + 1
        by_format = dict(sorted(by_format.items(), key=lambda x: -x[1]))

        by_decade: dict = {}
        for v in all_v:
            y = v.get("year")
            try:
                d = f"{(int(y) // 10) * 10}s"
            except (TypeError, ValueError):
                d = "Unknown"
            by_decade[d] = by_decade.get(d, 0) + 1
        by_decade = dict(sorted(by_decade.items()))

        by_artist: dict = {}
        for v in all_v:
            a = (v.get("artist") or "Unknown").strip()
            by_artist[a] = by_artist.get(a, 0) + 1
        top_artists = sorted(by_artist.items(), key=lambda x: -x[1])[:12]

        return {
            "total": total,
            "artists": artists,
            "total_cost": round(total_cost, 2),
            "total_market_low": round(total_market, 2),
            "wants": wants,
            "currency": currency,
            "db_path": db_path,
            "by_genre": by_genre,
            "by_condition": by_condition,
            "by_format": by_format,
            "by_decade": by_decade,
            "top_artists": top_artists,
            "portfolio_history": self.get_price_history(limit=90),
        }

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_config(self, key: str, default: str = "") -> str:
        row = self.conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def set_config(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
        )
        self.conn.commit()

    def get_all_config(self) -> dict:
        rows = self.conn.execute("SELECT key, value FROM config").fetchall()
        return {r[0]: r[1] for r in rows}

    # ------------------------------------------------------------------
    # JSON sync (SharePoint-friendly)
    # ------------------------------------------------------------------

    def export_to_json(self, json_path: str | Path) -> int:
        vinyls = self.get_all_vinyls()
        for v in vinyls:
            v.pop("id", None)
        wants = self.get_all_wants()
        for w in wants:
            w.pop("id", None)
        config = self.get_all_config()
        data = {"vinyls": vinyls, "wantlist": wants, "config": config}
        Path(json_path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Saved %d vinyls + %d wants to %s", len(vinyls), len(wants), json_path)
        return len(vinyls)

    def import_from_json(self, json_path: str | Path) -> int:
        text = Path(json_path).read_text(encoding="utf-8")
        data = json.loads(text)
        return self.import_from_json_data(data)

    def import_from_json_data(self, data: dict) -> int:
        vinyls = data.get("vinyls", [])
        wants = data.get("wantlist", [])
        config = data.get("config", {})
        self.conn.execute("DELETE FROM vinyls")
        self.conn.execute("DELETE FROM wantlist")
        for v in vinyls:
            v.pop("id", None)
            if v:
                cols = ", ".join(v.keys())
                placeholders = ", ".join("?" for _ in v)
                self.conn.execute(
                    f"INSERT OR IGNORE INTO vinyls ({cols}) VALUES ({placeholders})",
                    list(v.values()),
                )
        for w in wants:
            w.pop("id", None)
            if w:
                cols = ", ".join(w.keys())
                placeholders = ", ".join("?" for _ in w)
                self.conn.execute(
                    f"INSERT OR IGNORE INTO wantlist ({cols}) VALUES ({placeholders})",
                    list(w.values()),
                )
        for k, val in config.items():
            self.conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (k, val)
            )
        self.conn.commit()
        logger.info("Loaded %d vinyls + %d wants", len(vinyls), len(wants))
        return len(vinyls)
 
