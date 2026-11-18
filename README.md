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

UI: http://localhost:8080, links: http://localhost:8001, analytics: http://localhost:8002

## Running a single service

```
cd services/links          # or services/analytics
pip install -r requirements.txt -r requirements-dev.txt
PORT=8001 ANALYTICS_URL=http://localhost:8002 python app.py
```

## Tests and coverage

```
cd services/links && python -m pytest --cov=. --cov-report=term
cd services/analytics && python -m pytest --cov=. --cov-report=term
```

Work in progress: SQL Server, migrations, CI/CD and Azure come in the next commits.
