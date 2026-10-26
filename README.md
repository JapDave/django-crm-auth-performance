# Django CRM: authentication and query-performance demonstration

A focused portfolio code sample maintained by **Jap Dave**. Built with AI assistance as a new engineering demonstration, not presented as previous client delivery. No client code, credentials or private records are included.

## What this demonstrates

- Django 5.2, Django REST Framework and PostgreSQL configuration.
- Contact and deal CRUD APIs with owner-scoped read/write access.
- Existing username/password sessions plus Google OAuth through django-allauth.
- Explicit authenticated Google-account linking instead of silently linking by matching email.
- Normalized contact emails, per-owner uniqueness and nonnegative deal amounts.
- Pagination, contact search, deal-stage filters and deterministic ordering.
- ORM query optimization and regression tests that catch N+1 queries.
- Docker/Compose setup and a PostgreSQL-backed GitHub Actions test workflow.

This is a backend example with a minimal landing page, allauth screens and DRF's browsable interface. It is not a complete CRM product or a React UI.

## Run locally (SQLite, no Docker required)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DJANGO_DEBUG=true
export EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://127.0.0.1:8000/. Register through `/accounts/signup/` and open the verification URL printed by the console mail backend. Existing password accounts remain supported. Never use the console email backend for production.

## PostgreSQL and Docker

```bash
cp .env.example .env
# Edit .env: set a random secret and matching database passwords.
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up --build -d web
```

Compose is a local demonstration configuration. PostgreSQL data lives in a named volume. Migrations are an explicit step, not run simultaneously by each web worker. Use a PostgreSQL DATABASE_URL for non-Docker deployments too. The included workflow runs tests against PostgreSQL; local validation in the authoring environment used SQLite because PostgreSQL and Docker were unavailable.

## Google authentication setup

1. Create a Google OAuth web client in your own Google Cloud project and configure its consent screen/test users.
2. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the environment. Do not commit them.
3. Register the exact redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/` for local development, and your HTTPS domain's corresponding path for deployment. Hostname and scheme must match.
4. Use `/accounts/google/login/` to sign in. The confirmation form initiates the handshake with POST; allauth handles the OAuth callback and state validation, with PKCE enabled.
5. To connect Google to an existing password account, sign in to that account first and use `/accounts/social/connections/`.

Google sign-in is configured, not live-provider verified in this repository's local test run. Tests cover the confirmation page and anti-auto-linking configuration, not Google's external consent/callback. Complete live callback, denied consent, expired state and existing-account collision checks before deployment. No Google tokens are persisted by this sample.

## API examples

Sign in using the browser. DRF uses session authentication and requires a CSRF token for unsafe requests.

```text
GET    /api/contacts/?search=acme
POST   /api/contacts/              {"name":"Avery","email":"avery@example.com","company":"Acme"}
PATCH  /api/contacts/1/            {"company":"Acme Labs"}
GET    /api/deals/?stage=qualified
POST   /api/deals/                 {"contact":1,"title":"Pilot","value":"500.00"}
PATCH  /api/deals/1/               {"stage":"won"}
```

The owner is assigned from the authenticated session. Foreign-owner IDs are hidden or rejected, including when reassigning a deal. Contacts with deals cannot be deleted accidentally: the endpoint returns HTTP 409. Each user has an isolated record collection; organization/team sharing is intentionally out of scope.

## Testing and measured query behavior

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
```

15 tests cover access isolation, owner override attempts, invalid reassignment, email duplicates, value validation, updates, filtering, deletion protection, CSRF and ORM query budgets.

| Scenario | Naive query count | Optimized query count |
| --- | ---: | ---: |
| Serialize 11 deals with a related contact name | 12 | 1 |
| Paginated deal API, 25 returned records | Not benchmarked | 2 (count + joined page) |
| Paginated contact API with deal counts | Not benchmarked | 2 (count + annotated page) |

These are reproducible query-count assertions from SQLite tests, not latency benchmarks or production performance claims. `select_related` loads contact fields with deals. `Count` computes contact deal counts without a query per record. Test fixtures and assertions are in `crm/tests.py`. Indexes support owner/time and contact/stage lookups; production usefulness should be checked using representative PostgreSQL data and EXPLAIN ANALYZE.

## Deployment handoff and boundaries

- Set DEBUG=false, a strong secret, exact ALLOWED_HOSTS and real email settings.
- Terminate HTTPS at a configured reverse proxy. HTTPS redirects and secure cookies are on when DEBUG=false. Configure trusted proxy headers only for a proxy you control; never trust arbitrary forwarded headers.
- Run migrations, `collectstatic`, and `check --deploy`; serve static assets via your proxy or static host. The image does not serve static files itself.
- Back up and test restore of PostgreSQL before schema changes. Run tests in staging and retain rollback artifacts.
- Add deployment-specific rate limiting, monitoring, secret management and a documented OAuth/provider smoke test.
- No live cloud deployment, production load test, penetration test, concurrency stress test or client code audit has been performed. Duplicate insert races are protected by a database constraint but do not yet have custom API error translation.
- Allauth registration requires email verification. Do not expose alternative login endpoints as a substitute if email verification is an application-wide access policy; DRF's `/api-auth/` is for development and should be removed or restricted before deployment.

## Structure

`config/`: settings, URL routing and WSGI. `crm/models.py`: schema and constraints. `crm/serializers.py`: API validation. `crm/views.py`: scoped querysets and CRUD behavior. `crm/tests.py`: security and query regression tests.

References: [Django query optimization](https://docs.djangoproject.com/en/5.2/topics/db/optimization/), [allauth Google provider](https://docs.allauth.org/en/latest/socialaccount/providers/google.html), [allauth social account configuration](https://docs.allauth.org/en/latest/socialaccount/configuration.html).
