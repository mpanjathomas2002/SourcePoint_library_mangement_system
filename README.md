# SourcePoint — Library Management System

**Version:** 1.1.0 | **Stack:** Django 4.2 + Supabase + Google Gemini AI
**License:** MIT | **Status:** Production-Ready

---

## Quick Start (5 minutes)

```bash
cd sourcepoint/backend
python -m venv venv && source venv/bin/activate
pip install -r ../requirements.txt
cp ../.env.example ../.env        # Edit .env with your values
python manage.py migrate
python manage.py seed_data         # 40 books, 20 users, 5 admins
python manage.py runserver         # http://127.0.0.1:8000
```

> **No Supabase yet?** Leave SUPABASE_DB_HOST empty — app auto-uses SQLite locally.

---

## Demo Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Super Admin | superadmin@sourcepoint.lib | SuperAdmin@2024 |
| Admin | alice.admin@sourcepoint.lib | Admin@2024 |
| User | james.okonkwo@mail.com | User@2024 |

Login redirects automatically by role — no manual role selection needed.

---

## Project Structure

```
sourcepoint/
├── backend/
│   ├── manage.py
│   ├── sourcepoint/        settings.py, urls.py, wsgi.py
│   ├── users/              Custom User model, auth, role management
│   ├── library/            Books, categories, borrowing, ratings
│   │   └── management/commands/
│   │       ├── seed_data.py        Load 40 books + 20 users
│   │       └── clear_mock_data.py  Remove all mock data
│   ├── ai_assistant/       Google Gemini AI (chat, summaries, recommendations)
│   ├── templates/
│   │   └── index.html      Full single-page app (all UI in one file)
│   └── static/             CSS/JS/images
├── requirements.txt        All free Python packages
├── .env.example            Environment variable template
├── Procfile                Railway/Heroku deployment
└── runtime.txt             Python version pin
```

---

## Role Permissions

| Feature | User | Admin | Super Admin |
|---------|:----:|:-----:|:-----------:|
| Browse & search catalog | YES | YES | YES |
| Borrow books (choose period) | YES | YES | YES |
| Rate & review books | YES | YES | YES |
| AI chat, summaries, recommendations | YES | YES | YES |
| Delete own account | YES | YES | NO |
| Add/edit/delete books | NO | YES | YES |
| Create/delete categories | NO | YES | YES |
| Suspend/restore users | NO | YES | YES |
| View all borrowings | NO | YES | YES |
| Change borrow settings | NO | YES | YES |
| Clear mock data (one button) | NO | YES | YES |
| Delete any user | NO | NO | YES |
| Create/delete admin accounts | NO | NO | YES |

---

## AI Assistant (Sage) — Google Gemini Free Tier

Free limits: 15 requests/minute, 1M tokens/month, no credit card.

Get key: https://aistudio.google.com/app/apikey
Add to .env: GEMINI_API_KEY=your-key-here

Capabilities:
- Natural language book search
- Book summaries (cached after first generation)
- Personalized recommendations from borrowing history
- General Q&A about books and library policies

---

## Managing Mock Data

Via admin dashboard button: Dashboard -> "Clear Mock Data"

Via command:
  python manage.py clear_mock_data     # remove all mock data
  python manage.py seed_data           # re-seed (safe to repeat)

Via API (requires admin token):
  DELETE /api/v1/library/mock-data/
  DELETE /api/v1/auth/mock-data/

---

## Key API Endpoints

Auth:
  POST /api/v1/auth/register/          Register (email + password)
  POST /api/v1/auth/login/             Login (returns JWT tokens)
  POST /api/v1/auth/logout/            Logout
  GET/PUT /api/v1/auth/profile/        View/update profile
  DELETE /api/v1/auth/account/delete/  Delete own account

Books:
  GET /api/v1/library/books/           Browse (?search=&category=&ordering=)
  GET /api/v1/library/books/<id>/      Book detail + reviews
  POST /api/v1/library/books/create/   Add book (admin)
  DELETE /api/v1/library/books/<id>/   Delete book (admin)
  POST /api/v1/library/books/<id>/rate/ Rate 1-5 stars

Borrowing:
  POST /api/v1/library/borrow/         Borrow {book_id, requested_days}
  POST /api/v1/library/borrow/<id>/return/  Return book
  GET /api/v1/library/my-books/        Your bookshelf

Categories:
  GET /api/v1/library/categories/      All categories
  POST /api/v1/library/categories/     Create (admin)
  DELETE /api/v1/library/categories/<id>/  Delete (admin)

AI:
  POST /api/v1/ai/chat/                Chat with Sage {message, history}
  GET /api/v1/ai/books/<id>/summary/   Generate book summary
  GET /api/v1/ai/recommendations/      Personalized picks

Admin:
  GET /api/v1/library/admin/stats/     Dashboard statistics
  GET /api/v1/library/settings/        Borrow settings
  PUT /api/v1/library/settings/        Update settings
  GET /api/v1/auth/users/              List users
  POST /api/v1/auth/users/<id>/suspend/    Suspend user
  POST /api/v1/auth/users/<id>/unsuspend/ Restore user
  DELETE /api/v1/auth/users/<id>/delete/  Delete user (superadmin)
  POST /api/v1/auth/admins/            Create admin (superadmin, max 5)
  DELETE /api/v1/auth/admins/<id>/     Remove admin (superadmin)

---

## Deployment

### Railway (recommended)
```bash
npm install -g @railway/cli
railway login && railway init && railway up
```
Set env vars in Railway dashboard.

### Render
Build: pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
Start: gunicorn sourcepoint.wsgi:application --bind 0.0.0.0:$PORT

### Pre-deploy checklist
- Set DEBUG=False in .env
- Set a strong DJANGO_SECRET_KEY
- Set ALLOWED_HOSTS to your domain
- Run: python manage.py collectstatic
- Update yourdomain.com in templates/index.html (3 occurrences)

---

## Troubleshooting

DB hostname crash:
  Leave SUPABASE_DB_HOST empty to use SQLite automatically.
  If set, verify the host format: db.yourproject.supabase.co
  Check your Supabase project is not paused (free tier pauses after inactivity).

AI not working:
  Add GEMINI_API_KEY to .env. Get free key at aistudio.google.com/app/apikey

Token blacklist error:
  Run: python manage.py migrate

Categories page empty:
  Add new categories after clearing mock data.

Static files missing in production:
  Run: python manage.py collectstatic --noinput

---

## SEO / Google Discovery

index.html includes: meta description, Open Graph, Twitter cards, schema.org Library JSON-LD.
Before deploying: replace all 3 occurrences of "yourdomain.com" in index.html with your real domain.
Submit to Google Search Console after deployment.

---

## Development Commands

python manage.py runserver          Start dev server
python manage.py migrate            Apply migrations
python manage.py makemigrations     Create migrations after model changes
python manage.py seed_data          Load mock data
python manage.py clear_mock_data    Remove mock data
python manage.py collectstatic      Collect static files for production
python manage.py shell              Django shell
