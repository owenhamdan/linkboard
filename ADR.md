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
