"""Discogs API client for the DuckDuckVinyl Dashboard."""
from __future__ import annotations

import re
import time
import logging

import requests

logger = logging.getLogger(__name__)

_API = "https://api.discogs.com"
_UA = "VinylCollectionDashboard/1.0"

# ── Currency conversion ────────────────────────────────────────────
_rate_cache: dict[str, tuple[float, float]] = {}   # "FROM->TO" -> (rate, timestamp)
_RATE_TTL = 3600  # cache rates for 1 hour


def _fx_rate(src: str, tgt: str) -> float | None:
    """Return exchange rate src→tgt. Uses frankfurter.app (free, no key)."""
    src, tgt = src.upper().strip(), tgt.upper().strip()
    if src == tgt:
        return 1.0
    key = f"{src}->{tgt}"
    cached = _rate_cache.get(key)
    if cached and (time.time() - cached[1]) < _RATE_TTL:
        return cached[0]
    try:
        resp = requests.get(
            f"https://api.frankfurter.dev/v1/latest",
            params={"from": src, "to": tgt},
            timeout=10,
        )
        if resp.status_code == 200:
            rate = resp.json().get("rates", {}).get(tgt)
            if rate:
                _rate_cache[key] = (float(rate), time.time())
                return float(rate)
    except Exception as exc:
        logger.warning("FX rate fetch %s→%s failed: %s", src, tgt, exc)
    return None


def _convert(price: float, src_currency: str, tgt_currency: str) -> float | None:
    """Convert *price* from *src_currency* to *tgt_currency*. Returns None on failure."""
    rate = _fx_rate(src_currency, tgt_currency)
    if rate is None:
        return None
    return round(price * rate, 2)


def _headers(token: str = "") -> dict:
    h = {"User-Agent": _UA}
    if token:
        h["Authorization"] = f"Discogs token={token}"
    return h


def extract_release_id(text: str) -> tuple[str, str]:
    """Returns (id, kind) where kind is 'release' or 'master'. Raises ValueError."""
    s = text.strip()
    # Bare number
    if re.match(r"^\d+$", s):
        return s, "release"
    # Release URL: /release/123 or /releases/123
    m = re.search(r"discogs\.com/(?:[^/]+/)*releases?/(\d+)", s)
    if m:
        return m.group(1), "release"
    # Master URL
    m = re.search(r"discogs\.com/(?:[^/]+/)*masters?/(\d+)", s)
    if m:
        return m.group(1), "master"
    raise ValueError(f"Cannot parse Discogs URL: {text!r}")


def fetch_vinyl_info(url_or_id: str, token: str = "", currency: str = "EUR") -> dict:
    """Fetch full release info + marketplace price stats."""
    release_id, kind = extract_release_id(url_or_id)

    if kind == "master":
        resp = requests.get(f"{_API}/masters/{release_id}", headers=_headers(token), timeout=15)
        resp.raise_for_status()
        master = resp.json()
        release_id = str(master.get("main_release", release_id))

    resp = requests.get(f"{_API}/releases/{release_id}", headers=_headers(token), timeout=15)
    resp.raise_for_status()
    data = resp.json()

    info = _parse_release(data, release_id)

    # Fetch marketplace price stats
    try:
        pr = requests.get(
            f"{_API}/marketplace/stats/{release_id}",
            headers=_headers(token),
            params={"curr_abbr": currency},
            timeout=15,
        )
        if pr.status_code == 200:
            ps = pr.json()
            lp = ps.get("lowest_price")
            if isinstance(lp, dict):
                info["lowest_price"] = lp.get("value")
                info["price_currency"] = lp.get("currency", currency)
            elif lp is not None:
                info["lowest_price"] = float(lp)
            info["num_for_sale"] = ps.get("num_for_sale", 0)
    except Exception as exc:
        logger.warning("Price fetch failed for release %s: %s", release_id, exc)

    return info


def refresh_price(release_id: str, token: str = "", currency: str = "EUR") -> dict:
    """Refresh marketplace price stats only."""
    result: dict = {"lowest_price": None, "num_for_sale": 0, "price_currency": currency}
    try:
        resp = requests.get(
            f"{_API}/marketplace/stats/{release_id}",
            headers=_headers(token),
            params={"curr_abbr": currency},
            timeout=15,
        )
        if resp.status_code == 200:
            ps = resp.json()
            lp = ps.get("lowest_price")
            if isinstance(lp, dict):
                result["lowest_price"] = lp.get("value")
                result["price_currency"] = lp.get("currency", currency)
            elif lp is not None:
                result["lowest_price"] = float(lp)
            result["num_for_sale"] = ps.get("num_for_sale", 0)
    except Exception as exc:
        logger.warning("Price refresh failed for %s: %s", release_id, exc)
    return result


def refresh_price_by_condition(release_id: str, token: str = "", currency: str = "EUR",
                               condition: str = "") -> dict:
    """
    Fetch per-condition suggested prices from /marketplace/price_suggestions/{release_id}.
    Returns e.g. {"NM": {"min": 20.0, "max": 20.0, "median": 20.0, "count": 1}, "_all": {...}}
    _all aggregates across all conditions so min/max show the full price range.
    Requires a Discogs personal access token.
    """
    _cond_map = {
        "M": "Mint (M)", "NM": "Near Mint (NM or M-)",
        "VG+": "Very Good Plus (VG+)", "VG": "Very Good (VG)",
        "G+": "Good Plus (G+)", "G": "Good (G)",
        "F": "Fair (F)", "P": "Poor (P)",
    }
    _long_to_short = {long: short for short, long in _cond_map.items()}

    if not token:
        return {}

    try:
        resp = requests.get(
            f"{_API}/marketplace/price_suggestions/{release_id}",
            headers=_headers(token),
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("Price suggestions fetch %s → %s", release_id, resp.status_code)
            return {}
        result: dict = {}
        all_prices: list[float] = []
        for long_cond, price_info in resp.json().items():
            short = _long_to_short.get(long_cond)
            if not short or not isinstance(price_info, dict):
                continue
            val = price_info.get("value")
            if val is None:
                continue
            val = float(val)
            src_cur = price_info.get("currency", currency)
            if src_cur.upper() != currency.upper():
                converted = _convert(val, src_cur, currency)
                if converted is not None:
                    val = converted
                else:
                    continue
            val = round(val, 2)
            result[short] = {"min": val, "max": val, "median": val, "count": 1}
            all_prices.append(val)

        # Build _all aggregate — min/max span the full condition price range
        if all_prices:
            all_prices.sort()
            n = len(all_prices)
            mid = n // 2
            median = all_prices[mid] if n % 2 else round((all_prices[mid - 1] + all_prices[mid]) / 2, 2)
            result["_all"] = {
                "min": all_prices[0],
                "max": all_prices[-1],
                "median": median,
                "count": n,
            }
        return result
    except Exception as exc:
        logger.warning("Price suggestions fetch failed for %s: %s", release_id, exc)
        return {}


def search_releases(query: str, token: str = "", page: int = 1, per_page: int = 10) -> list[dict]:
    """Search Discogs for releases matching the query. Returns a list of brief result dicts."""
    params = {
        "q": query,
        "type": "release",
        "per_page": per_page,
        "page": page,
    }
    resp = requests.get(f"{_API}/database/search", headers=_headers(token), params=params, timeout=15)
    resp.raise_for_status()
    out = []
    for r in resp.json().get("results", []):
        # Prefer cover_image (larger) then thumb
        cover = r.get("cover_image") or r.get("thumb") or ""
        out.append({
            "release_id": str(r.get("id", "")),
            "title": r.get("title", ""),
            "label": ", ".join(r.get("label", [])) if isinstance(r.get("label"), list) else (r.get("label") or ""),
            "catno": r.get("catno", ""),
            "format": ", ".join(r.get("format", [])) if isinstance(r.get("format"), list) else (r.get("format") or ""),
            "country": r.get("country", ""),
            "year": r.get("year", ""),
            "genre": ", ".join(r.get("genre", [])),
            "style": ", ".join(r.get("style", [])),
            "cover_image_url": cover,
            "discogs_url": f"https://www.discogs.com/release/{r.get('id', '')}",
            "num_for_sale": r.get("community", {}).get("have", 0),
        })
    return out


def _parse_release(data: dict, release_id: str) -> dict:
    artists = ", ".join(
        a.get("name", "").rstrip(" ,*").strip()
        for a in data.get("artists", [])
    ) or data.get("artists_sort", "")

    labels, catnos = [], []
    for lbl in data.get("labels", []):
        n = lbl.get("name", "")
        c = lbl.get("catno", "")
        if n and "Not On Label" not in n:
            labels.append(n)
        if c and c.upper() != "NONE":
            catnos.append(c)

    fmt_parts = []
    for fmt in data.get("formats", []):
        parts = [fmt.get("name", "")]
        qty = fmt.get("qty", "1")
        if qty and qty != "1":
            parts.append(f"x{qty}")
        parts.extend(fmt.get("descriptions", []))
        fmt_parts.append(", ".join(p for p in parts if p))

    # Prefer full-size uri then uri150 (thumbnail)
    images = data.get("images", [])
    cover = ""
    for img in images:
        if img.get("type") == "primary":
            cover = img.get("uri") or img.get("uri150") or ""
            break
    if not cover and images:
        cover = images[0].get("uri") or images[0].get("uri150") or ""

    rid = str(data.get("id", release_id))
    return {
        "release_id": rid,
        "title": data.get("title", "").strip(),
        "artist": artists,
        "year": data.get("year") or 0,
        "label": ", ".join(labels),
        "catno": ", ".join(catnos),
        "format": " / ".join(fmt_parts),
        "country": data.get("country", ""),
        "genre": ", ".join(data.get("genres", [])),
        "style": ", ".join(data.get("styles", [])),
        "discogs_url": f"https://www.discogs.com/release/{rid}",
        "cover_image_url": cover,
        "tracklist_count": len(data.get("tracklist", [])),
        "lowest_price": None,
        "num_for_sale": 0,
        "price_currency": "EUR",
    }
