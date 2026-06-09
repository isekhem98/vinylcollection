"""Flask web dashboard for DuckDuckVinyl."""
from __future__ import annotations

import json
import json
import logging
import queue
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, render_template, request, send_file, stream_with_context

from database import Database, DEFAULT_DB_PATH, _app_root
from discogs_client import fetch_vinyl_info, refresh_price, refresh_price_by_condition, search_releases

_CONFIG_FILE = _app_root() / "config.json"
_SETTINGS_FILE = _app_root() / "settings.json"
_DATA_FILE = _app_root() / "data.json"

logger = logging.getLogger(__name__)

_db: Database | None = None
_log_queue: queue.Queue[str] = queue.Queue()


def _bundle_root() -> Path:
    import sys
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


app = Flask(
    __name__,
    template_folder=str(_bundle_root() / "templates"),
)
app.config["SECRET_KEY"] = b"vinyl-secret-key"


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


class QueueLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        _log_queue.put(self.format(record))


# ------------------------------------------------------------------
# API – Vinyls
# ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/vinyls")
def api_vinyls():
    return jsonify(get_db().get_all_vinyls())


@app.route("/api/vinyls", methods=["POST"])
def api_add_vinyl():
    data = request.get_json() or {}
    db = get_db()
    # Check for duplicate
    rid = data.get("release_id", "")
    if rid and db.get_vinyl_by_release_id(rid):
        return jsonify({"error": f"Release {rid} is already in your collection."}), 409

    # Only keep known columns (prevent SQL injection via column names)
    allowed = {
        "release_id", "title", "artist", "year", "label", "catno", "format",
        "country", "genre", "style", "condition", "purchase_price", "purchase_date",
        "discogs_url", "cover_image_url", "lowest_price", "price_currency",
        "num_for_sale", "tracklist_count", "notes", "tags", "condition_prices",
        "purchase_location",
    }
    fields = {k: v for k, v in data.items() if k in allowed and v not in (None, "")}
    new_id = db.add_vinyl(**fields)
    logger.info("Added vinyl: %s – %s", data.get("artist"), data.get("title"))
    _log_queue.put(f"[DONE] Added: {data.get('artist')} – {data.get('title')}")
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/vinyls/<int:vinyl_id>", methods=["PATCH"])
def api_update_vinyl(vinyl_id: int):
    data = request.get_json() or {}
    allowed = {
        "title", "artist", "year", "label", "catno", "format", "country",
        "genre", "style", "condition", "purchase_price", "purchase_date",
        "discogs_url", "notes", "tags", "purchase_location",
    }
    fields = {k: v for k, v in data.items() if k in allowed}
    get_db().update_vinyl(vinyl_id, **fields)
    return jsonify({"ok": True})


@app.route("/api/vinyls/<int:vinyl_id>", methods=["DELETE"])
def api_delete_vinyl(vinyl_id: int):
    db = get_db()
    v = db.get_vinyl(vinyl_id)
    if v:
        db.delete_vinyl(vinyl_id)
        _log_queue.put(f"[INFO] Deleted: {v.get('artist')} – {v.get('title')}")
    return jsonify({"ok": True})


@app.route("/api/vinyls/bulk-edit", methods=["PATCH"])
def api_bulk_edit():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
        return jsonify({"error": "ids required"}), 400
    allowed = {"tags", "condition", "notes", "purchase_location"}
    fields = {k: v for k, v in data.get("fields", {}).items() if k in allowed}
    mode = data.get("mode", "replace")  # replace | append
    if not fields:
        return jsonify({"error": "No fields to update"}), 400
    db = get_db()
    updated = 0
    for vid in ids:
        v = db.get_vinyl(int(vid))
        if not v:
            continue
        update_fields = {}
        for k, val in fields.items():
            if mode == "append" and k in ("tags", "notes"):
                existing = (v.get(k) or "").strip()
                if existing:
                    update_fields[k] = existing + ", " + val
                else:
                    update_fields[k] = val
            else:
                update_fields[k] = val
        db.update_vinyl(int(vid), **update_fields)
        updated += 1
    _log_queue.put(f"[DONE] Bulk-edited {updated} records.")
    return jsonify({"ok": True, "updated": updated})


# ------------------------------------------------------------------
# API – Discogs fetch + search
# ------------------------------------------------------------------

@app.route("/api/fetch-discogs", methods=["POST"])
def api_fetch_discogs():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    db = get_db()
    token = db.get_config("discogs_token", "")
    currency = db.get_config("currency", "EUR")
    try:
        info = fetch_vinyl_info(url, token=token, currency=currency)
        # Also fetch condition price stats so min/avg/max show on add
        rid = info.get("release_id", "")
        if rid:
            cond_prices = refresh_price_by_condition(rid, token=token, currency=currency)
            if not cond_prices and info.get("lowest_price") is not None:
                lp = float(info["lowest_price"])
                cond_prices = {"_all": {"min": lp, "max": lp, "median": lp, "count": 1}}
            if cond_prices:
                info["condition_prices"] = json.dumps(cond_prices)
        return jsonify(info)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.error("Discogs fetch error: %s", exc)
        return jsonify({"error": f"Discogs error: {exc}"}), 502


@app.route("/api/search-discogs")
def api_search_discogs():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    db = get_db()
    token = db.get_config("discogs_token", "")
    try:
        results = search_releases(q, token=token, per_page=12)
        return jsonify(results)
    except Exception as exc:
        logger.error("Discogs search error: %s", exc)
        return jsonify({"error": str(exc)}), 502


# ------------------------------------------------------------------
# API – Wantlist
# ------------------------------------------------------------------

@app.route("/api/wants")
def api_wants():
    return jsonify(get_db().get_all_wants())


@app.route("/api/wants", methods=["POST"])
def api_add_want():
    data = request.get_json() or {}
    db = get_db()
    rid = data.get("release_id", "")
    if rid and db.get_want_by_release_id(rid):
        return jsonify({"error": "Already in your wantlist."}), 409
    allowed = {
        "release_id", "title", "artist", "year", "label", "format", "genre",
        "cover_image_url", "discogs_url", "lowest_price", "price_currency",
        "num_for_sale", "max_price", "notes",
    }
    fields = {k: v for k, v in data.items() if k in allowed and v not in (None, "")}
    new_id = db.add_want(**fields)
    _log_queue.put(f"[INFO] Added to wantlist: {data.get('artist')} – {data.get('title')}")
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/wants/<int:want_id>", methods=["PATCH"])
def api_update_want(want_id: int):
    data = request.get_json() or {}
    allowed = {"max_price", "notes", "condition", "purchase_price", "purchase_date"}
    fields = {k: v for k, v in data.items() if k in allowed}
    get_db().update_want(want_id, **fields)
    return jsonify({"ok": True})


@app.route("/api/wants/<int:want_id>", methods=["DELETE"])
def api_delete_want(want_id: int):
    get_db().delete_want(want_id)
    return jsonify({"ok": True})


@app.route("/api/wants/<int:want_id>/move-to-collection", methods=["POST"])
def api_move_want(want_id: int):
    data = request.get_json() or {}
    db = get_db()
    try:
        new_id = db.move_want_to_collection(want_id, **data)
        _log_queue.put(f"[DONE] Moved wantlist item #{want_id} to collection.")
        return jsonify({"ok": True, "id": new_id})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/wants/refresh-prices", methods=["POST"])
def api_refresh_want_prices():
    db = get_db()
    wants = [w for w in db.get_all_wants() if w.get("release_id")]
    token = db.get_config("discogs_token", "")
    currency = db.get_config("currency", "EUR")

    def _worker():
        for w in wants:
            result = refresh_price(w["release_id"], token=token, currency=currency)
            db.update_want(w["id"], **{k: v for k, v in result.items() if k in ("lowest_price", "price_currency", "num_for_sale")})
            time.sleep(0.5)
        _log_queue.put(f"[DONE] Refreshed prices for {len(wants)} wantlist items.")

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"ok": True, "count": len(wants)})


# ------------------------------------------------------------------
# API – Price refresh
# ------------------------------------------------------------------

@app.route("/api/vinyls/<int:vinyl_id>/refresh-price", methods=["POST"])
def api_refresh_price(vinyl_id: int):
    db = get_db()
    v = db.get_vinyl(vinyl_id)
    if not v:
        return jsonify({"error": "Not found"}), 404
    rid = v.get("release_id", "")
    if not rid:
        return jsonify({"error": "No release_id stored"}), 400
    token = db.get_config("discogs_token", "")
    currency = db.get_config("currency", "EUR")
    result = refresh_price(rid, token=token, currency=currency)
    vinyl_condition = v.get("condition", "")
    cond_prices = refresh_price_by_condition(rid, token=token, currency=currency, condition=vinyl_condition)
    if not cond_prices and result.get("lowest_price") is not None:
        lp = float(result["lowest_price"])
        cond_prices = {"_all": {"min": lp, "max": lp, "median": lp, "count": 1}}
    result["condition_prices"] = json.dumps(cond_prices) if cond_prices else None
    db.update_vinyl(vinyl_id, **result)
    # Record price snapshot
    db.add_price_snapshot(rid, result.get("lowest_price"), result.get("condition_prices"))
    resp_data = {k: v for k, v in result.items() if k != "condition_prices"}
    resp_data["condition_prices"] = cond_prices
    return jsonify({"ok": True, **resp_data})


@app.route("/api/refresh-all-prices", methods=["POST"])
def api_refresh_all_prices():
    """Refresh marketplace prices for all vinyls in background."""
    db = get_db()
    vinyls = [v for v in db.get_all_vinyls() if v.get("release_id")]
    token = db.get_config("discogs_token", "")
    currency = db.get_config("currency", "EUR")

    def _worker():
        updated = 0
        for v in vinyls:
            result = refresh_price(v["release_id"], token=token, currency=currency)
            vinyl_condition = v.get("condition", "")
            cond_prices = refresh_price_by_condition(v["release_id"], token=token, currency=currency, condition=vinyl_condition)
            if not cond_prices and result.get("lowest_price") is not None:
                lp = float(result["lowest_price"])
                cond_prices = {"_all": {"min": lp, "max": lp, "median": lp, "count": 1}}
            result["condition_prices"] = json.dumps(cond_prices) if cond_prices else None
            db.update_vinyl(v["id"], **result)
            db.add_price_snapshot(v["release_id"], result.get("lowest_price"), result.get("condition_prices"))
            updated += 1
            lp = result.get("lowest_price")
            lp_str = f"{lp:.2f} {result.get('price_currency','')}" if lp else "N/A"
            _log_queue.put(f"[INFO] {v.get('artist')} – {v.get('title')}: {lp_str}")
            time.sleep(0.5)  # Respect Discogs rate limit
        _log_queue.put(f"[DONE] Refreshed prices for {updated} records.")

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"ok": True, "count": len(vinyls)})


# ------------------------------------------------------------------
# API – Image proxy (for Discogs CDN images)
# ------------------------------------------------------------------

@app.route("/api/image-proxy")
def api_image_proxy():
    import requests as req
    url = request.args.get("url", "")
    if not url:
        return "", 404
    # Security: only proxy from Discogs CDN or their S3 mirrors
    parsed = urlparse(url)
    if parsed.netloc not in ("i.discogs.com", "img.discogs.com", "s.discogs.com", "images.discogs.com", "discogs-database-images.s3.amazonaws.com"):
        return "", 403
    token = get_db().get_config("discogs_token", "")
    headers = {"User-Agent": "VinylCollectionDashboard/1.0"}
    if token:
        headers["Authorization"] = f"Discogs token={token}"
    try:
        r = req.get(url, headers=headers, timeout=10, stream=True)
        content_type = r.headers.get("content-type", "image/jpeg")
        return Response(r.iter_content(4096), content_type=content_type)
    except Exception:
        return "", 404


# ------------------------------------------------------------------
# API – Stats
# ------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    return jsonify(get_db().get_stats())


# ------------------------------------------------------------------
# API – Update covers
# ------------------------------------------------------------------

@app.route("/api/update-covers", methods=["POST"])
def api_update_covers():
    """Refresh cover_image_url for all vinyls that have a Discogs release_id.
    This runs in background to avoid blocking the server and respects a short delay
    between requests to avoid hitting Discogs rate limits.
    """
    db = get_db()
    token = db.get_config("discogs_token", "")
    vinyls = [v for v in db.get_all_vinyls() if v.get("release_id")]

    def _worker():
        updated = 0
        for v in vinyls:
            try:
                info = fetch_vinyl_info(v["release_id"], token=token, currency=db.get_config("currency", "EUR"))
                new_cover = info.get("cover_image_url")
                if new_cover and new_cover != (v.get("cover_image_url") or ""):
                    db.update_vinyl(v["id"], cover_image_url=new_cover)
                    updated += 1
                    _log_queue.put(f"[INFO] Updated cover for {v.get('artist')} - {v.get('title')}")
                time.sleep(0.6)
            except Exception as exc:
                _log_queue.put(f"[WARN] Cover update failed for {v.get('release_id')}: {exc}")
        _log_queue.put(f"[DONE] Refreshed covers for {updated} records.")

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"ok": True, "count": len(vinyls)})


@app.route("/api/price-history")
def api_price_history():
    rid = request.args.get("release_id", "")
    db = get_db()
    history = db.get_price_history(release_id=rid if rid else None)
    return jsonify(history)


# ------------------------------------------------------------------
# API – Config
# ------------------------------------------------------------------

@app.route("/api/config")
def api_config():
    db = get_db()
    return jsonify(db.get_all_config())


@app.route("/api/config", methods=["PATCH"])
def api_config_update():
    data = request.get_json() or {}
    db = get_db()
    for k, v in data.items():
        db.set_config(str(k), str(v))
    return jsonify({"ok": True})


# ------------------------------------------------------------------
# API – Export CSV
# ------------------------------------------------------------------

@app.route("/api/export/csv")
def api_export_csv():
    import io, csv
    vinyls = get_db().get_all_vinyls()
    if not vinyls:
        return jsonify({"error": "No data"}), 404
    cols = ["artist", "title", "year", "label", "catno", "format", "country",
            "genre", "style", "condition", "purchase_price", "purchase_date",
            "purchase_location", "lowest_price", "price_currency", "num_for_sale",
            "tags", "notes", "discogs_url"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(vinyls)
    output = buf.getvalue().encode("utf-8-sig")
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=vinyl_collection.csv"},
    )


# ------------------------------------------------------------------
# API – JSON sync
# ------------------------------------------------------------------

@app.route("/api/export/share")
def api_export_share():
    """Generate a standalone read-only HTML page of the collection."""
    import html as htmlmod
    db = get_db()
    vinyls = db.get_all_vinyls()
    stats = db.get_stats()
    currency = stats.get("currency", "EUR")
    # Sanitise for embedding in HTML
    for v in vinyls:
        v.pop("id", None)
        # Parse condition_prices for JS consumption
        if isinstance(v.get("condition_prices"), str):
            try:
                v["condition_prices"] = json.loads(v["condition_prices"])
            except Exception:
                v["condition_prices"] = {}
    # Embed cover images as base64 so gallery works when the file is opened offline
    import base64 as _b64
    import requests as _req
    _allowed = ('img.discogs.com', 'i.discogs.com', 'images.discogs.com',
                'discogs-database-images.s3.amazonaws.com')
    img_cache: dict = {}
    for v in vinyls:
        url = v.get("cover_image_url")
        if url and url not in img_cache:
            try:
                p = urlparse(url)
                if p.scheme in ('http', 'https') and p.hostname and any(p.hostname.endswith(d) for d in _allowed):
                    r = _req.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"})
                    if r.ok:
                        ct = r.headers.get("content-type", "image/jpeg").split(";")[0]
                        img_cache[url] = f"data:{ct};base64,{_b64.b64encode(r.content).decode()}"
            except Exception:
                pass
        if url and url in img_cache:
            v["cover_image_url"] = img_cache[url]
    data_json = json.dumps(vinyls, default=str)
    stats_json = json.dumps({
        "total": stats["total"], "artists": stats["artists"],
        "total_cost": stats["total_cost"], "total_market_low": stats["total_market_low"],
        "currency": currency,
        "by_genre": stats["by_genre"], "by_condition": stats["by_condition"],
        "by_decade": stats["by_decade"], "by_format": stats["by_format"],
        "top_artists": stats["top_artists"],
    }, default=str)
    page = _share_page(data_json, stats_json, currency)
    return Response(
        page.encode("utf-8"),
        mimetype="text/html",
        headers={"Content-Disposition": "attachment; filename=my_vinyl_collection.html"},
    )


def _share_page(data_json: str, stats_json: str, currency: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DuckDuckVinyl</title>
<style>
:root{{--bg:#0f0f13;--surface:#1a1a24;--border:#2a2a3a;--text:#e8e8f0;--text-dim:#7878a0;--accent:#7c3aed;--green:#22c55e;--red:#ef4444;--orange:#f59e0b;--blue:#3b82f6;--purple:#a855f7;}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--text);font-family:"Segoe UI",system-ui,sans-serif;font-size:14px;padding:20px}}
a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}
.hdr{{text-align:center;margin-bottom:20px}}.hdr h1{{font-size:1.4rem;font-weight:700}}.hdr h1 span{{color:var(--accent)}}
.hdr .sub{{font-size:.75rem;color:var(--text-dim);margin-top:4px}}
.stats{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:16px}}
.sc{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 18px;text-align:center;min-width:100px}}
.sc .n{{font-size:1.3rem;font-weight:700}}.sc .l{{font-size:.68rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}
.sc.green .n{{color:var(--green)}}.sc.blue .n{{color:var(--blue)}}.sc.purple .n{{color:var(--purple)}}.sc.orange .n{{color:var(--orange)}}
.controls{{margin-bottom:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.controls input{{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:6px;font-size:.82rem;width:260px}}
.controls input:focus{{outline:none;border-color:var(--accent)}}
.badge{{display:inline-block;padding:1px 7px;border-radius:8px;font-size:.68rem;font-weight:700;text-transform:uppercase}}
.cond-m,.cond-nm{{background:rgba(34,197,94,.15);color:var(--green)}}
.cond-vgp{{background:rgba(59,130,246,.15);color:var(--blue)}}
.cond-vg{{background:rgba(168,85,247,.15);color:var(--purple)}}
.cond-gp{{background:rgba(245,158,11,.15);color:var(--orange)}}
.cond-g,.cond-f,.cond-p{{background:rgba(239,68,68,.15);color:var(--red)}}
.tag{{display:inline-block;padding:1px 6px;border-radius:6px;font-size:.62rem;font-weight:600;background:rgba(124,58,237,.15);color:var(--accent);margin:0 2px 1px 0}}
.view-toggle{{display:flex;gap:6px;margin-bottom:12px;justify-content:center}}
.view-toggle button{{padding:5px 14px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);font-size:.78rem;cursor:pointer}}
.view-toggle button.active{{border-color:var(--accent);color:var(--accent)}}
.twrap{{overflow-x:auto;border:1px solid var(--border);border-radius:8px;max-height:70vh;overflow-y:auto}}
table{{width:100%;border-collapse:collapse;font-size:.8rem}}
thead th{{position:sticky;top:0;z-index:2;background:var(--surface);padding:7px 10px;text-align:left;font-weight:600;cursor:pointer;white-space:nowrap;border-bottom:2px solid var(--border)}}
thead th:hover{{color:var(--accent)}}
tbody tr{{border-bottom:1px solid var(--border);transition:background .1s}}tbody tr:hover{{background:rgba(124,58,237,.07)}}
td{{padding:5px 10px;white-space:nowrap;vertical-align:middle}}
td.wrap{{white-space:normal;max-width:160px;line-height:1.3}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;display:none}}
.gc{{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}}
.gc img{{width:100%;aspect-ratio:1;object-fit:cover;display:block}}
.gc .ph{{width:100%;aspect-ratio:1;background:var(--bg);display:flex;align-items:center;justify-content:center;font-size:2.5rem;color:var(--text-dim)}}
.gc .gi{{padding:8px 10px}}.gc .ga{{font-size:.72rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.gc .gt{{font-size:.68rem;color:var(--text-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cnt{{font-size:.78rem;color:var(--text-dim);margin-left:auto}}
.pr{{font-size:.72rem}}.pr .med{{font-weight:600}}.pr .dim{{color:var(--text-dim);font-size:.65rem}}
.bars{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:14px}}
.bar-card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px}}
.bar-card .bt{{font-size:.72rem;font-weight:600;color:var(--text-dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}}
.bar-row{{margin-bottom:6px}}
.bar-row .bl{{display:flex;justify-content:space-between;font-size:.72rem;margin-bottom:2px}}
.bar-row .bl span:last-child{{color:var(--text-dim)}}
.bar-row .bv{{background:var(--border);border-radius:3px;height:6px}}
.bar-row .bf{{background:var(--accent);height:6px;border-radius:3px}}
</style></head><body>
<div class="hdr"><h1>&#9835; <span>Vinyl</span> Collection</h1>
<div class="sub">Shared collection &middot; Generated {__import__('datetime').date.today().isoformat()}</div></div>
<div class="stats" id="stats"></div>
<div class="view-toggle"><button class="active" onclick="setView('table',this)">&#9776; Table</button><button onclick="setView('gallery',this)">&#9638; Gallery</button></div>
<div class="controls"><input type="text" id="q" placeholder="Search artist, title, genre..." oninput="render()"><span class="cnt" id="cnt"></span></div>
<div class="twrap" id="tw"><table><thead><tr>
<th onclick="srt('artist')">Artist</th><th onclick="srt('title')">Title</th><th onclick="srt('year')">Year</th>
<th onclick="srt('label')">Label</th><th onclick="srt('format')">Format</th><th onclick="srt('genre')">Genre</th>
<th onclick="srt('condition')">Cond</th><th onclick="srt('purchase_price')">Cost</th><th>Mkt</th><th>Tags</th><th>Notes</th>
</tr></thead><tbody id="tb"></tbody></table></div>
<div class="gallery" id="gv"></div>
<div class="bars" id="bars"></div>
<script>
const D={data_json};
const S={stats_json};
const C='{currency}';
let sc='artist',sa=true;
function condBadge(c){{if(!c)return'';const m={{M:'cond-m',NM:'cond-nm','VG+':'cond-vgp',VG:'cond-vg','G+':'cond-gp',G:'cond-g',F:'cond-f',P:'cond-p'}};return`<span class="badge ${{m[c]||'cond-g'}}">${{c}}</span>`;}}
function mktCell(v){{const cp=v.condition_prices||{{}};let st=null,matched=false;if(v.condition&&cp[v.condition]&&typeof cp[v.condition]==='object'){{st=cp[v.condition];matched=true;}}else if(cp._all&&typeof cp._all==='object')st=cp._all;if(st&&st.median!=null){{const allSt=cp._all;const rangeStr=matched&&allSt&&allSt.min!=null&&allSt.min!==allSt.max?`<div class="dim">${{allSt.min.toFixed(2)}} – ${{allSt.max.toFixed(2)}}</div>`:'';if(matched&&st.min===st.max)return`<div class="pr" style="color:var(--blue)"><span class="med">${{st.median.toFixed(2)}}</span> <span class="dim">${{C}}</span><div class="dim">${{v.condition}} suggested</div>${{rangeStr}}</div>`;if(st.min!==st.max)return`<div class="pr"><span class="med">${{st.median.toFixed(2)}}</span> <span class="dim">${{C}}</span><div class="dim">${{st.min.toFixed(2)}} – ${{st.max.toFixed(2)}}</div></div>`;return`<div class="pr"><span class="dim" style="font-size:.6rem">from</span> <span class="med">${{st.median.toFixed(2)}}</span> <span class="dim">${{C}}</span></div>`;}}if(v.lowest_price!=null)return`<div class="pr"><span class="dim" style="font-size:.6rem">from</span> <span class="med">${{Number(v.lowest_price).toFixed(2)}}</span> <span class="dim">${{C}}</span></div>`;return'<span class="dim">-</span>';}}
function tags(t){{if(!t)return'';return t.split(',').map(s=>s.trim()).filter(Boolean).map(s=>`<span class="tag">${{s}}</span>`).join('');}}
function srt(col){{if(sc===col)sa=!sa;else{{sc=col;sa=true;}}render();}}
function setView(mode,btn){{document.querySelectorAll('.view-toggle button').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.getElementById('tw').style.display=mode==='table'?'':'none';document.getElementById('gv').style.display=mode==='gallery'?'grid':'none';}}
function render(){{const q=(document.getElementById('q').value||'').toLowerCase();let d=D.filter(v=>!q||Object.values(v).map(x=>String(x||'')).join(' ').toLowerCase().includes(q));
d.sort((a,b)=>{{let va=a[sc]??'',vb=b[sc]??'';if(['year','purchase_price','lowest_price'].includes(sc)){{va=Number(va)||0;vb=Number(vb)||0;}}else{{va=String(va).toLowerCase();vb=String(vb).toLowerCase();}}return va<vb?(sa?-1:1):va>vb?(sa?1:-1):0;}});
document.getElementById('cnt').textContent=d.length+' / '+D.length;
document.getElementById('tb').innerHTML=d.map(v=>`<tr><td style="font-weight:500">${{v.artist||''}}</td><td>${{v.title||''}}</td><td style="color:var(--text-dim)">${{v.year||''}}</td><td style="color:var(--text-dim)">${{v.label||''}}</td><td style="color:var(--text-dim)">${{v.format||''}}</td><td style="color:var(--text-dim)">${{v.genre||''}}</td><td>${{condBadge(v.condition)}}</td><td>${{v.purchase_price!=null?v.purchase_price.toFixed(2)+' '+C:'<span class="dim">-</span>'}}</td><td>${{mktCell(v)}}</td><td class="wrap" style="font-size:.72rem">${{tags(v.tags)}}</td><td class="wrap" style="color:var(--text-dim);font-size:.75rem">${{v.notes||''}}</td></tr>`).join('');
document.getElementById('gv').innerHTML=d.map(v=>{{const src=v.cover_image_url?v.cover_image_url:'';return`<div class="gc">${{src?`<img src="${{src}}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="ph" style="display:none">&#9835;</div>`:`<div class="ph">&#9835;</div>`}}<div class="gi"><div class="ga">${{v.artist||''}}</div><div class="gt">${{v.title||''}}</div></div></div>`;}}).join('');
}}
function renderStats(){{const s=S;const t=D.length;const cost=D.reduce((a,v)=>a+(v.purchase_price||0),0);const mkt=D.reduce((a,v)=>{{const cp=v.condition_prices||{{}};let m=null;if(v.condition&&cp[v.condition]&&typeof cp[v.condition]==='object')m=cp[v.condition].median;else if(cp._all&&typeof cp._all==='object')m=cp._all.median;if(m==null)m=v.lowest_price;return a+(m||0);}},0);const pl=mkt-cost;
document.getElementById('stats').innerHTML=`<div class="sc blue"><div class="n">${{t}}</div><div class="l">Records</div></div><div class="sc purple"><div class="n">${{s.artists||0}}</div><div class="l">Artists</div></div><div class="sc orange"><div class="n">${{cost.toFixed(0)}} ${{C}}</div><div class="l">Total Cost</div></div><div class="sc green"><div class="n">${{mkt.toFixed(0)}} ${{C}}</div><div class="l">Market Value</div></div><div class="sc ${{pl>=0?'green':''}}"><div class="n">${{(pl>=0?'+':'')+pl.toFixed(0)}} ${{C}}</div><div class="l">P&amp;L</div></div>`;
function bar(title,data,total,lim){{const e=Object.entries(data||{{}}).sort((a,b)=>b[1]-a[1]);const shown=lim?e.slice(0,lim):e;const mx=Math.max(...shown.map(x=>x[1]))||1;return`<div class="bar-card"><div class="bt">${{title}}</div>${{shown.map(([l,c])=>`<div class="bar-row"><div class="bl"><span>${{l}}</span><span>${{c}} (${{total?Math.round(c/total*100):0}}%)</span></div><div class="bv"><div class="bf" style="width:${{Math.round(c/mx*100)}}%"></div></div></div>`).join('')}}</div>`;}}
document.getElementById('bars').innerHTML=bar('By Condition',s.by_condition,t)+bar('By Genre',s.by_genre,t,10)+bar('By Decade',s.by_decade,t)+bar('By Format',s.by_format,t,8);if(s.top_artists&&s.top_artists.length){{const taRows=s.top_artists.slice(0,10).map(([n,c],i)=>`<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid var(--border)"><span style="font-size:.68rem;color:var(--text-dim);width:18px;text-align:right">${{i+1}}</span><span style="flex:1;font-size:.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{n}}</span><span style="font-size:.72rem;color:var(--accent);font-weight:600">${{c}}</span></div>`).join('');document.getElementById('bars').insertAdjacentHTML('afterend',`<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px;margin-top:12px"><div style="font-size:.72rem;font-weight:600;color:var(--text-dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">Top Artists</div>${{taRows}}</div>`);}}
}}
renderStats();render();
</script></body></html>"""


@app.route("/api/sync/save", methods=["POST"])
def api_sync_save():
    db = get_db()
    count = db.export_to_json(_DATA_FILE)
    _log_queue.put(f"[DONE] Saved {count} records to data.json")
    return jsonify({"ok": True, "count": count})


@app.route("/api/sync/refresh", methods=["POST"])
def api_sync_refresh():
    if not _DATA_FILE.exists():
        return jsonify({"error": "data.json not found — save first."}), 404
    db = get_db()
    count = db.import_from_json(_DATA_FILE)
    _log_queue.put(f"[DONE] Loaded {count} records from data.json")
    return jsonify({"ok": True, "count": count})


@app.route("/api/import/json", methods=["POST"])
def api_import_json():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file provided"}), 400
    try:
        data = json.loads(f.read().decode("utf-8"))
    except Exception:
        return jsonify({"error": "Invalid JSON file"}), 400
    if not isinstance(data, dict) or "vinyls" not in data:
        return jsonify({"error": 'Invalid format — expected {"vinyls": [...], "wantlist": [...], "config": {...}}'}), 400
    db = get_db()
    count = db.import_from_json_data(data)
    wants_count = len(data.get("wantlist", []))
    _log_queue.put(f"[DONE] Imported {count} records + {wants_count} wantlist items from JSON file.")
    return jsonify({"ok": True, "count": count, "wants": wants_count})


# ------------------------------------------------------------------
# SSE log stream
# ------------------------------------------------------------------

@app.route("/api/logs/stream")
def api_logs_stream():
    def generate():
        while True:
            try:
                msg = _log_queue.get(timeout=30)
                yield f"data: {json.dumps({'msg': msg})}\n\n"
            except queue.Empty:
                yield ": ping\n\n"
    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------

def create_app(db_path: str | Path = DEFAULT_DB_PATH) -> Flask:
    global _db
    _db = Database(db_path)

    # Auto-load from data.json if DB is empty
    if _DATA_FILE.exists() and _db.get_count() == 0:
        try:
            count = _db.import_from_json(_DATA_FILE)
            logger.info("Auto-loaded %d records from data.json", count)
        except Exception as exc:
            logger.warning("Failed to auto-load data.json: %s", exc)

    handler = QueueLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    return app


def main(db_path: str = "", port: int = 5000):
    import webbrowser, socket
    from database import DEFAULT_DB_PATH
    actual = db_path or str(DEFAULT_DB_PATH)
    flask_app = create_app(actual)
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "127.0.0.1"
    url = f"http://127.0.0.1:{port}"
    logger.info("DuckDuckVinyl Dashboard at %s", url)
    logger.info("Also accessible at http://%s:%s", ip, port)
    threading.Timer(1.5, webbrowser.open, args=[url]).start()
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)