# Linkboard

A link shortener with click analytics. Paste a long URL, get a short slug, and see how many people clicked it, on which days and from which sites.

Assignment 2 splits the monolith into two services, each in its own folder with its own database:
* **links** (`services/links/`): create, look up, list and delete short links, and redirect `/<slug>`
* **analytics** (`services/analytics/`): record clicks and report stats per slug

The links service calls analytics over HTTP (`ANALYTICS_URL`) when a link is followed or deleted. Every call has a timeout; if analytics is down, redirects still work and the click is simply not counted.

The UI is a static page in `ui/` that calls both services from the browser. Their URLs come from `ui/config.js`.

## Running locally with Docker

```
docker compose up --build
```

SQL Server starts in a container first, then `db-init` runs `db/init.sql` to create one database and one login per service, then both services apply their migrations on startup. On Apple Silicon, turn on Rosetta emulation in Docker Desktop.

UI: http://localhost:8080, links: http://localhost:8001, analytics: http://localhost:8002

## Running a single service

```
cd services/links          # or services/analytics
pip install -r requirements.txt -r requirements-dev.txt
docker compose up -d db db-init     # a SQL Server to talk to
DATABASE_URL=mssql://links_user:LocalDev_links_123@localhost:1433/links \
  PORT=8001 ANALYTICS_URL=http://localhost:8002 python app.py
```

## Database migrations

Each service keeps its SQL Server schema in `services/<name>/migrations/` as numbered SQL files (`001_init.sql`, `002_...`). On startup `migrate.py` applies any file not yet listed in the `schema_migrations` table, in order, and logs `applying migration <file>`. Applied files are never edited; a change goes in a new numbered file.

## System description

`system.yaml` describes both services, their environment variables, the calls between them and their Azure resources, in the format of `system.schema.json` (provided by the course, unchanged). Each service has an `openapi.yaml`. CI checks all three:

* `check-jsonschema` validates `system.yaml` against the schema
* `openapi-spec-validator` validates both OpenAPI documents
* `tools/check_system.py` checks `system.yaml` against the code: every environment variable read in the code is listed, every endpoint one service calls exists in the other's OpenAPI document
* `tests/test_openapi.py` in each service checks the OpenAPI paths against the app's real routes

## Tests and coverage

```
docker compose up -d db db-init     # tests need SQL Server
cd services/links && python -m pytest --cov=. --cov-report=term
cd services/analytics && python -m pytest --cov=. --cov-report=term
```

Work in progress: CD to Azure comes in the next commits.

## Commit history note

There are no commits on Thursday 19 November 2026. I missed that day, so the history covers fewer than the six days the brief asks for.
