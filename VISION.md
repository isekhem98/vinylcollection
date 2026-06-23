# DuckDuckShelf — Vision Document

> From vinyl tracker to a cozy home for everything you collect.

---

## Is this achievable?

**Yes, fully.** Every part of this vision can be built with the same stack already in use — Flask, SQLite, vanilla JS, and HTML/CSS. No new frameworks needed. The interactive room is pure SVG + CSS + JavaScript. The multi-collection backend is a schema extension. The biggest investment is art and UX polish, not technical complexity.

---

## The Big Idea

A personal collectibles dashboard that opens on an illustrated, interactive room. Shelves hold your records. A glass cabinet holds figurines. A bookcase holds books. A TV unit holds games. A cassette deck sits on a side table. You click on any object in the room and it opens that collection's management view — the same kind of table/gallery/stats interface the vinyl section already has, adapted for each category.

The room is your homepage. The collections are rooms within the room.

---

## The Room

The homepage is an SVG illustration of a cozy, dimly lit collector's room rendered directly in the browser — no images to load, no external assets, fully themeable with CSS variables so it changes color with your chosen theme.

### Clickable hotspots

| Object in the room | Collection it opens |
|---|---|
| Record shelf / turntable | Vinyl |
| Cassette deck / tape rack | Cassettes |
| CD tower / binder | CDs |
| Bookcase | Books |
| Display cabinet / shelf | Figurines & statues |
| TV unit / shelf beneath it | Video games |
| Magazine rack | Comics & magazines |
| Any empty shelf | Add a custom category |

Each hotspot has a subtle glow or pulse animation on hover, and a small badge showing how many items are in that collection. Clicking slides the room away and brings up the collection view.

### Room personality
- Ambient details change based on what you own: the turntable spins if you have vinyls, the TV flickers if you have games, a book is open on the desk if you have books.
- The room respects your chosen theme — Liner Notes gives it warm candlelight tones, Terminal makes it a neon-green underground lair, Midnight makes it a moonlit minimalist space.
- Optionally: a clock on the wall shows the real time.

---

## The Collections

Each collection category gets its own tailored management view. They all share the same core engine (add, edit, delete, search, sort, gallery/table toggle, stats) but with fields and integrations appropriate to the category.

### Vinyl *(existing, carry forward)*
- Fields: artist, title, label, year, format, condition, purchase price, market price, tracklist, genre, style, country, tags, notes
- Integrations: Discogs lookup, price refresh, YouTube/Spotify search
- Extras: wantlist, per-condition price ranges, portfolio P&L tracking

### Cassettes *(new)*
- Fields: artist, title, label, year, type (album / mixtape / demo), condition, purchase price
- Extras: runtime, tape type (Type I/II/IV), has original case, has j-card
- Integration: Discogs has cassette releases — same lookup flow as vinyl

### CDs *(new)*
- Fields: artist, title, label, year, edition (standard / deluxe / box set / promo), condition, purchase price
- Extras: disc count, barcode, has OBI strip, has booklet
- Integration: Discogs lookup (releases filtered to CD format)

### Books *(new)*
- Fields: title, author, publisher, year, genre, edition, condition, purchase price, read status (unread / reading / finished / re-reading)
- Extras: ISBN, page count, signed copy flag, personal rating, notes / highlights
- Integration: Open Library API (free, no key required) for auto-fill by ISBN or title search — cover image, author, publisher, year, page count

### Video Games *(new)*
- Fields: title, platform, developer, publisher, year, genre, condition, complete-in-box status (game only / with box / CIB), region, purchase price
- Extras: completion status (unplayed / in progress / completed / 100%), playtime estimate, personal rating
- Integration: IGDB or RAWG API for auto-fill — cover art, genre, platform, release year

### Figurines & Statues *(new)*
- Fields: name, series/franchise, manufacturer, scale, year, condition, purchase price, display location, original box present
- Extras: limited edition flag, edition number (e.g. 142/500), materials, height
- Integration: Manual entry only (no single authoritative database exists); photo upload support important here

### Comics & Magazines *(new)*
- Fields: title, issue number, publisher, year, condition (CGC grade or standard), purchase price
- Extras: key issue flag, graded copy, slab details, story arc
- Integration: ComicVine API for auto-fill (free tier available)

### Custom Categories *(new)*
- User can define their own category with a custom name, icon, and set of fields
- Fields can be: text, number, date, dropdown (user-defined options), checkbox
- Covers anything: stamps, coins, sneakers, watches, trading cards, whisky bottles, etc.

---

## Cross-Collection Features

These live at the app level, across all collections.

### Dashboard / Overview
A summary view accessible from the room (e.g. clicking a notice board or desk) showing:
- Total item count across all collections
- Total estimated value
- Recently added items (last 7 days, across all categories)
- Wishlist items approaching their target price
- A combined portfolio value chart over time

### Global Search
A single search bar that queries across all collections at once. Results are grouped by category with their category icon.

### Wantlist (universal)
The current vinyl wantlist generalised — any item in any category can be added to a wishlist with a max price. Price alerts trigger when market prices drop below the threshold (for categories with market data).

### Export & Backup
- Export any collection or all collections to CSV or JSON
- Import from JSON (for migration or restore)
- The existing save/refresh sync pattern carries forward

### Statistics
A dedicated stats view per collection and a combined view:
- Collection value over time (if prices are tracked)
- Breakdown by decade, genre, condition, format, etc.
- Rarest items (fewest copies for sale on the market)
- Most valuable items
- Items bought below / above market

---

## Technical Architecture

### Backend changes

The current single-collection SQLite schema expands to a multi-collection model. Two approaches:

**Option A — One table per category** (simpler, recommended to start)
Each collection gets its own table with its own columns. The existing `vinyls` table stays as-is. New tables like `books`, `games`, `figurines` are added. Shared logic (add, edit, delete, stats, wantlist) lives in a base class that each collection subclasses.

**Option B — Generic items table with a JSON fields column** (more flexible)
A single `items` table with `category`, `name`, and a `fields` JSON blob. Better for custom categories. Slightly harder to query and index efficiently. Can be added on top of Option A later.

Recommended path: start with Option A for the built-in categories, add Option B for custom categories.

### Frontend changes

The room SVG is a single `<svg>` block inline in a new `room.html` template. It uses `<a>` tags or `onclick` handlers on hotspot shapes. The existing `index.html` collection interface becomes a reusable template that each category populates with its own field definitions, column config, and API endpoints.

A lightweight client-side router (no framework needed — just `history.pushState`) handles transitions between the room view and collection views.

### API changes

Routes get a category prefix:
```
/api/collection/vinyl       (existing, renamed)
/api/collection/books
/api/collection/games
/api/collection/figurines
/api/collection/custom/:id
```

A category registry (a Python dict or small config file) defines which categories exist, their display name, icon, table name, and field schema.

### External API integrations summary

| Category | API | Key required |
|---|---|---|
| Vinyl / Cassettes / CDs | Discogs | Optional (free tier works) |
| Books | Open Library | No |
| Games | RAWG | Free tier (no key for basic use) |
| Comics | ComicVine | Free key |
| Figurines | None (manual) | — |
| Custom | None | — |

---

## Phased Build Plan

### Phase 1 — The Room (homepage)
Build the SVG room with clickable hotspots, hover glows, item count badges, and smooth transition to the existing vinyl collection. The room is the new entry point; everything else stays the same.

**Effort: medium.** Mostly design and SVG work. No backend changes.

### Phase 2 — Multi-collection backend
Extend the database and API to support 2–3 new categories (e.g. cassettes, books, games). Each gets its own table, routes, and field config. The frontend collection view becomes parameterised so it renders any category.

**Effort: medium-high.** Mostly backend, some frontend.

### Phase 3 — External integrations
Add Open Library lookup for books, RAWG for games. Mirror the existing Discogs fetch pattern.

**Effort: low-medium per integration.** Each one is a self-contained client module.

### Phase 4 — Cross-collection features
Global search, universal wantlist, combined stats dashboard, portfolio chart.

**Effort: medium.** Mostly frontend, some backend aggregation queries.

### Phase 5 — Custom categories
The generic field builder so users can define their own collection types from the UI.

**Effort: high.** Most complex piece — dynamic schema, dynamic form builder, dynamic table renderer.

### Phase 6 — Room personality & polish
Ambient animations, theme-reactive room art, time-aware details (day/night room lighting), item count reflected visually in the room (empty vs full shelves).

**Effort: medium.** Pure frontend / SVG animation.

---

## What to rename it

DuckDuckVinyl made sense for a vinyl tracker. A few ideas for the expanded version:

- **DuckDuckShelf** — keeps the brand, signals the shelf/room concept
- **The Shelf** — simple, cozy, direct
- **Curio** — a cabinet of curiosities; fits the collector spirit perfectly
- **Hoard** — affectionate, a little cheeky
- **The Cabinet** — nods to the display cabinet / collector's room

---

## Summary

The core vision — a cozy interactive room as a homepage for a multi-collection tracker — is technically straightforward with the existing stack. The hardest part is not code, it's the SVG room art and deciding how detailed to make it. Everything else is an extension of patterns already in the codebase. A first playable version of the room (Phase 1) could be built in a single focused session.
