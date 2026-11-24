# Architecture Decision Records

Note: all five entries were written on the same day as the deadline, so this log does not meet the three commit dates requirement.

## 1. Backend language and framework
Date: 2026-10-04
Status: Decided
Context: The app is a small JSON API plus one HTML page, and I need to explain every line of it in the comprehension check.
Decision: Python with Flask, using the built in `sqlite3` module instead of an ORM.
Alternatives considered: Django, rejected because its admin, ORM and project structure are far more than two small domains need. FastAPI, rejected because async and Pydantic models add concepts I would have to explain without gaining anything at this size.
Consequences: Only one runtime dependency (Flask), so the container in Assignment 2 stays small. I write SQL by hand, which is more code but easy to read.

## 2. Scoping the two domains to be separable
Date: 2026-10-04
Status: Decided
Context: The links domain and the analytics domain should be able to become separate services later.
Decision: Each domain lives in its own package (`links/`, `analytics/`) with its own table, and neither package imports the other. Only `app.py` calls both, for example when a redirect happens it asks `links` for the URL and then tells `analytics` to record the click.
Alternatives considered: One `models.py` with both tables and functions mixed together, rejected because the seam between domains would disappear.
Consequences: The seam is the two calls in `app.py`'s `follow` route; later that `record_click` call becomes an HTTP call or event to an analytics service.

## 3. No foreign key between clicks and links
Date: 2026-10-04
Status: Decided
Context: `clicks` needs to know which link was clicked.
Decision: `clicks.slug` is plain text matching `links.slug`, with an index but no FOREIGN KEY constraint.
Alternatives considered: `clicks.link_id` as a FOREIGN KEY to `links.id` with ON DELETE CASCADE, rejected because it ties the two tables to the same database, which blocks splitting analytics into its own service.
Consequences: Deleting a link does not clean clicks automatically, so `app.py` calls `delete_clicks` explicitly. Orphan clicks are possible if that call fails.

## 4. Testing approach
Date: 2026-10-04
Status: Decided
Context: The 70% coverage target is on core business logic, not routing.
Decision: Unit tests call `links/service.py` and `analytics/service.py` directly using an in memory SQLite database, prioritising validation rules, duplicate slugs and the stats grouping.
Alternatives considered: Testing through the Flask test client, rejected as the main approach because it tests routing glue rather than the logic.
Consequences: 98% coverage on both domains, but `app.py` routes are only checked manually.

## 5. No user accounts
Date: 2026-10-04
Status: Decided
Context: Real link shorteners let each user see only their own links.
Decision: I did not build authentication; every link and its stats are public.
Alternatives considered: Flask login with a users table, rejected because it adds a third domain and password handling that is not needed to show the two required domains.
Consequences: Anyone can delete any link. Accounts would be the first thing to add before real users.

## 6. The split
Date: 2026-11-20
Status: Decided
Context: Assignment 2 turns the monolith into two services. ADR 2 put the seam between the links domain and the analytics domain, with `app.py` as the only place that called both.
Decision: Two services, `links` and `analytics`, each in `services/<name>/` with its own database. The seam is where ADR 2 put it and it held: the two packages never imported each other, so splitting them only meant replacing the calls in `app.py` with HTTP. Two things cross the seam, both server side from links to analytics: recording a click when `/<slug>` is followed (`POST /clicks`) and removing clicks when a link is deleted (`DELETE /clicks/{slug}`). The UI calls analytics directly for stats (`GET /stats/{slug}`), because stats need nothing from links. If analytics is down or slower than `ANALYTICS_TIMEOUT_S` (2 seconds), links degrades: the redirect still works and the click is not counted, and a delete returns 200 with a warning that the clicks were not removed.
Alternatives considered: Having links ask analytics on every redirect and fail if it did not answer, rejected because the main job of a link shortener is the redirect and it should not depend on the stats. Letting the UI record clicks, rejected because a person following a short link never loads the UI. Retrying failed calls, rejected because a redirect that waits for retries feels broken, and one lost click is cheaper.
Consequences: Lost clicks while analytics is down, and orphan clicks if a delete reaches links but not analytics. Both are accepted and logged. Only two kinds of call cross the seam, which suggests it is in the right place.

## 7. Data and migrations
Date: 2026-11-24
Status: Decided
Context: The monolith kept both tables in one SQLite file. Assignment 2 needs one SQL Server database per service, and a schema that can change while the database already holds data.
Decision: `links` moved to the links database and `clicks` to the analytics database. Nothing had to be split, because ADR 3 had already avoided a foreign key between them: `clicks.slug` stays a plain column. Migrations are numbered T-SQL files per service, applied on startup by my own small runner (`migrate.py`): it creates `schema_migrations` if needed, runs each pending file in order inside one transaction, records its version in the same transaction, and stops the service if a migration fails. Files are split on `GO` lines like sqlcmd does. Migrations are forward only. `001_init.sql` was rewritten from SQLite to T-SQL before it had ever been applied to a shared database; from the first deploy on, applied files are never edited and every change is a new file.
Alternatives considered: Alembic, rejected because it brings SQLAlchemy as well, which I would also have to explain, to run a handful of SQL files. Creating the schema on boot as in Assignment 1, rejected because it cannot change a table that already holds data.
Integrity lost at the seam: SQL Server cannot check that a click belongs to an existing link, because the links live in another database. Compensation: links only records clicks for slugs it just found, and deleting a link asks analytics to delete its clicks. If analytics is down at that moment the clicks are left behind as orphans; they are harmless, because stats are only shown for links that exist.
Recovery plan for a bad migration in production: because each migration runs in a transaction, a failing one rolls back fully, the service refuses to start, and the previous revision keeps serving (Container Apps only switches traffic to a healthy revision). The fix is a new migration file in a new commit, never an edit of the bad one. If a migration succeeded but damaged data, Azure SQL point in time restore brings the database back to a copy from before the deploy, and a forward migration undoes the schema change.
Consequences: With at most one replica, migrations never run twice at the same time. With more replicas they would need a lock (`sp_getapplock`) or a separate migration job.
