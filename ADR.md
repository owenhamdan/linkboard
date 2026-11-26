# Architecture Decision Records

Note: all five entries were written on the same day as the deadline, so this log does not meet the three commit dates requirement.

## 1. Backend language and framework
Date: 2026-10-04
Status: Superseded by [7] for storage (SQLite became SQL Server); Python and Flask still hold
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
Status: Superseded by [9]
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

## 8. Serverless hosting on Azure
Date: 2026-11-26
Status: Decided
Context: The system has to run on Azure for Students, cost nothing while idle, and be deployed only by the pipeline.
Decision: Everything lives in `rg-ohamdan-ieu2023` in francecentral, all pay per use:
* two Container Apps (`ohamdan-ieu2023-links`, `ohamdan-ieu2023-analytics`) on the Consumption plan in one environment, 0.25 vCPU and 0.5 GiB each, minimum 0 and maximum 1 replica: billed per second only while a replica runs, and free within the monthly free grant at this traffic
* the Log Analytics workspace Azure created with the environment, for container logs: billed per GB ingested, free up to 5 GB a month
* one SQL logical server `ohamdan-ieu2023-sql` with two serverless General Purpose Gen5 databases (0.5 to 1 vCore) on the free offer: no cost, auto pause after 60 minutes, 32 GB each
* one Storage account `ohamdanieu2023ui` with the static website: cents per GB stored and served
* the managed identity `ohamdan-ieu2023-github` (free) and images on GHCR (free for a public repository), instead of Azure Container Registry, which has a fixed monthly fee
Consequences of scale to zero: after a few idle minutes no replica runs. The first request starts a container (several seconds), and if the database has also paused, it needs up to about a minute to resume. `db.connect` therefore retries with exponential backoff (2, 4, 8, 16 then 30 seconds, about two minutes in total) on connection errors such as 40613. Container Apps may answer that first request with 503 after about 30 seconds; the UI waits up to 40 seconds and then shows "a service is starting up, please try again". Migrations run at startup inside `create_app`, which is safe only because there is at most one replica, so two copies never migrate at once; gunicorn's worker timeout is raised to 180 seconds so a slow resume plus migrations is not killed. The post deploy health check retries for about five minutes to allow for all of this.
Alternatives considered: A minimum of one replica, rejected because it bills all the time for a system that is idle almost all the time. Azure App Service or a VM, rejected because they are always on and out of scope.
At 100x traffic: raise the maximum replicas and scale on HTTP concurrency; move migrations out of startup into a separate step in the pipeline (a Container Apps job) or guard them with `sp_getapplock`; give each process a connection pool instead of one shared connection; turn off auto pause or move the databases off the free offer, whose 100,000 vCore seconds a month would run out; record clicks asynchronously (a queue between links and analytics) so a redirect never waits for analytics; and put a CDN in front of the static website.

## 9. Pipeline and testing
Date: 2026-11-26
Status: Decided
Context: Every push must be tested, every merge to main deployed with no manual steps, and CD must only deploy a commit CI has passed. ADR 4 tested against in memory SQLite, which no longer matches production.
Decision: `ci.yml` runs on every push to a branch and every pull request, and `cd.yml` calls it through `workflow_call` on main, so the deploy jobs `need` a green CI on the same commit. CI gates on:
* ruff, so style and unused code problems fail early
* unit and API tests per service against a real SQL Server container with a password generated for each run, because T-SQL (`IDENTITY`, `CAST(... AS DATE)`, `GO` batches) cannot be tested on SQLite
* coverage of at least 70% per service (`--cov-fail-under=70`, tests excluded); today links is about 91% and analytics about 87%
* `system.yaml` against `system.schema.json`, both OpenAPI documents against the OpenAPI spec, `tools/check_system.py` (environment variables and cross service endpoints against the code) and a test per service comparing `openapi.yaml` with the app's real routes, so the documents cannot drift from the code
* integration tests across the seam on the whole compose stack
* building both images
Cross seam test: `tests/integration/test_seam.py` runs against `docker compose up`, not against a stub, because the thing worth testing is the real HTTP call with its real timeout. It follows a link and checks analytics counted it, deletes a link and checks its clicks are gone, then runs `docker compose stop analytics` (the exact scenario of the brief) and checks links still redirects within 5 seconds, stays healthy, and warns on delete. Inside the links unit tests, the analytics client is replaced by a stub or an unreachable address, which tests the failure branches quickly without Docker.
Deliberately not tested: the UI's JavaScript (checked by hand in the browser); Azure only behaviour such as a paused database answering 40613, which only the post deploy health check exercises; load and concurrency, since there is one replica with one worker; and the migration's host name extraction on unusual URLs (with a user name or port), because every stored URL already passed `validate_url`.
Consequences: A CI run takes about four minutes, mostly starting SQL Server. A red run never reaches Azure, and CI never connects to Azure SQL, so it never wakes or bills the serverless databases.

## 10. Deliberately not built: a message queue for clicks
Date: 2026-11-26
Status: Decided
Context: Recording a click is a synchronous HTTP call from links to analytics during the redirect. If analytics is slow, every redirect waits up to the 2 second timeout; if it is down, the click is lost.
Decision: Not built. A queue (Azure Service Bus or Storage Queues) between links and analytics would let links publish a "clicked" event and return the redirect at once, with analytics consuming events at its own pace and no clicks lost while it is down. It is out of scope (section 1c), adds a third moving part to deploy, monitor and pay for, and at this traffic a lost click is cheap.
When it would be worth building: when lost clicks start to matter (for example if stats were billed to customers), when analytics latency starts to show in redirect times at the 95th percentile, or around 100x today's traffic, when analytics needs to scale separately from links and batch its writes. Deleting clicks for a deleted link would then also become an event, which removes the orphan clicks described in ADR 7.
Consequences: Today the redirect path depends on analytics' latency, bounded by `ANALYTICS_TIMEOUT_S`, and clicks are lost while analytics is unavailable. Both are logged.
