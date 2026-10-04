# AI Usage Log

| Date/commit | Tool | Prompt | Disposition | What changed and why | In my own words, how this works |
|---|---|---|---|---|---|

| 2026-10-04 | Claude | Generate the links domain (`links/service.py`) | Accepted | None | `create_link` checks the URL starts with http or https, checks a custom slug matches `SLUG_PATTERN` or makes a random 6 character one with `generate_slug`, then inserts. A duplicate slug hits the UNIQUE constraint, which raises `IntegrityError` and becomes a `LinkError`. TODO: rewrite in your own words |
| 2026-10-04 | Claude | Generate the analytics domain (`analytics/service.py`) | Accepted | None | `record_click` stores the slug and a cleaned referrer. `normalise_referrer` keeps only the host and strips `www.`, or returns `direct` if empty. `get_stats` runs three COUNT queries: total, grouped by `date(clicked_at)`, and grouped by referrer. TODO: rewrite in your own words |
| 2026-10-04 | Claude | Generate `app.py` and `db.py` | Accepted | None | `get_connection` creates `DATA_DIR`, opens SQLite and runs `SCHEMA` with CREATE IF NOT EXISTS, so no manual migration. `create_app` defines the routes; the `follow` route gets the link, calls `record_click`, then returns a 302 redirect. TODO: rewrite in your own words |
| 2026-10-04 | Claude | Generate tests | Modified | Two tests failed because slug `ie` was under the 3 character minimum, changed to `iex` | Tests use `get_connection(":memory:")` so each test gets a fresh empty database. TODO: rewrite in your own words |
| 2026-10-04 | Claude | Write README, ADR and this log | Accepted | None | TODO |
