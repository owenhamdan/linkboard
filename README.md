# Linkboard

A link shortener with click analytics. Paste a long URL, get a short slug, and see how many people clicked it, on which days and from which sites.

Two feature domains:
* **links** (`links/service.py`): create, look up, list and delete short links
* **analytics** (`analytics/service.py`): record clicks and report stats per slug

## Setup

```
git clone <repo url>
cd linkboard
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8000

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Port the server listens on (binds to `0.0.0.0`) |
| `DATA_DIR` | `data` | Folder for the SQLite file, which is `$DATA_DIR/linkboard.db` |

The database and tables are created automatically on first start. No manual migration.

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/api/links` | Body `{"url": "...", "slug": "optional"}` |
| GET | `/api/links` | List all links |
| DELETE | `/api/links/<slug>` | Delete a link and its clicks |
| GET | `/api/links/<slug>/stats` | Total, per day and per referrer clicks |
| GET | `/<slug>` | Redirects to the URL and records a click |

## Tests and coverage

```
python -m pytest --cov=links --cov=analytics --cov-report=term
```

Result: 13 tests passed, 98% coverage on `links` and `analytics`.
