# Smart Expense Tracker — Vercel Ready

Django-based Smart Expense Tracker with:
- 30-day free trial
- ₹99 Premium after the trial
- Dashboard, transactions, budgets, reports, EMI tracking, profile
- Receipt/image uploads
- Razorpay payment verification
- PostgreSQL in both local development and production

## Important database point

This project is **PostgreSQL-only**. SQLite and `db.sqlite3` are not used.
The project uses Django ORM + migrations, so you do **not** manually create every table.

Create a managed PostgreSQL database and set `DATABASE_URL` both locally and on Vercel.
The included Vercel build script automatically runs:

```bash
python manage.py migrate --noinput
```

on deployments when `DATABASE_URL` is present.

## Deploy to Vercel

Vercel has zero-configuration Django support: it detects `manage.py` and the Django WSGI application, so a `vercel.json` redirect or `/api` folder is not required.

### 1. Upload/push this project

The ZIP is arranged so that `manage.py`, `requirements.txt`, `pyproject.toml`, `expenses/`, and `smart_expense_tracker/` are at the project root.

For GitHub:
```bash
git init
git add .
git commit -m "Deploy Smart Expense Tracker"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

Then import the repository into Vercel. Keep the Vercel **Root Directory** at the folder that contains `manage.py`.

### 2. Create the production PostgreSQL database

In Vercel, add a PostgreSQL/Neon-compatible database from the project's Storage/database options. Copy the connection string it provides into:

```text
DATABASE_URL=...
```

Vercel's Django Notes example also documents PostgreSQL deployments and automatic migrations.

### 3. Add Vercel Environment Variables

Set these for **Production** (and Preview if you want preview deployments to use a separate database):

```text
DEBUG=0
SECRET_KEY=<strong-random-secret>
DATABASE_URL=<postgresql-connection-string>
DATABASE_SSL_REQUIRE=1
ALLOWED_HOSTS=<your-custom-domain>,.vercel.app
CSRF_TRUSTED_ORIGINS=https://<your-custom-domain>
RAZORPAY_KEY_ID=<your-live-key>
RAZORPAY_KEY_SECRET=<your-live-secret>
REGISTRATION_FEE=99.00
PAYMENT_DEMO_MODE=0
```

For a first deployment without Razorpay, leave the Razorpay keys blank. Do **not** enable `PAYMENT_DEMO_MODE=1` in production.

### 4. Deploy

Deploy from Vercel. The build script runs migrations automatically when `DATABASE_URL` exists.

### 5. Verify after deployment

Check:
- `/` — home page
- `/register/` — account creation
- `/login/` — login
- `/admin/` — Django admin
- Dashboard after creating an account
- Database rows are saved after creating a transaction
- Premium payment only activates after Razorpay verification

## Local development

1. Create a PostgreSQL database (for example with Neon, Supabase, Railway, or another PostgreSQL provider).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` to the PostgreSQL connection string.
3. Install dependencies and run migrations:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Production uploads

Vercel's application filesystem is not a permanent file store. Receipt/avatar uploads should use persistent object storage (such as Vercel Blob or another S3-compatible service) if those files must survive deployments/serverless instances. The current ZIP keeps the existing upload UI but does not pretend local disk is persistent.

## Security

- Never commit `.env`, database passwords, Razorpay secrets, or uploaded media.
- Use a strong production `SECRET_KEY`.
- Keep `DEBUG=0` in production.
- Keep `PAYMENT_DEMO_MODE=0` in production.
