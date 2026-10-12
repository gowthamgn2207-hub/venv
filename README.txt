FINTRACK - AI-Based Personal Finance Management and Expense Forecasting
Website with login + database + the real ML models.

DEMO LOGIN (already created, loaded with 24 months of sample data)
    Email   : demo@fintrack.app
    Password: Demo@1234
Anyone can also click "Create an account" and register their own login.

THE ML MODELS (all in ml.py, trained live on each user's own transactions)
  1. Naive Bayes + TF-IDF   -> "Auto-detect" category from the description
  2. Random Forest Regression -> next-month expense forecast per category
       - needs ~9 complete months of history; with less it falls back to a
         weighted moving average and SAYS so on the Forecast page
       - the Forecast page shows its error on 3 unseen months vs. a naive guess
  3. K-Means clustering     -> Lean / High-spend months (needs 6+ months)
  4. Recommendation rules   -> budget alerts, trends, savings-rate tips

RUN ON YOUR COMPUTER (needs Python 3.9+)
  Windows   : double-click run_windows.bat
  Mac/Linux : ./run_mac_linux.sh
  Browser opens at http://127.0.0.1:5000 (Chrome or Edge)

PUT IT ON THE INTERNET (so anyone can open a link)
  The link only exists after YOU deploy it. Easiest free option:
  PythonAnywhere.com
    1. Create a free account, open "Files", upload this folder (or the zip and unzip it).
    2. "Web" tab -> Add a new web app -> Flask -> Python 3.10+ -> manual configuration.
    3. Open a Bash console:  pip install --user -r requirements.txt
    4. In the Web tab set the WSGI file to:
           import sys; sys.path.insert(0, "/home/YOURNAME/fintrack_ml")
           from app import app as application
    5. Click Reload. Your link: https://YOURNAME.pythonanywhere.com
    SQLite data is kept on disk there, so users and transactions persist.
  Render.com / Railway also work (Procfile included) but their free disks are
  wiped on restart, so the database would reset unless you add a paid disk.

DEPLOY ON VERCEL (free Hobby plan)
  Vercel keeps no files between requests, so the SQLite file cannot be used there.
  The app switches to Postgres automatically when DATABASE_URL is set. Use the free Neon database from Vercel.
  1. Put this folder on GitHub (github.com -> New repository -> upload the files; do NOT upload venv or *.db).
  2. vercel.com -> sign in with GitHub -> Add New -> Project -> import that repo. Framework: Other/Flask (auto-detected).
     Do NOT press Deploy yet.
  3. Project -> Storage (or Marketplace) -> Neon Postgres -> Create -> connect it to the project.
     This adds DATABASE_URL for you.
  4. Project -> Settings -> Environment Variables, add:
        SECRET_KEY = any long random text (for example 40 random characters)   <- required
        HTTPS_ONLY = 1
  5. Deploy. Link: https://YOURPROJECT.vercel.app
  The first visit is slower (it creates the tables and the demo account, and loads scikit-learn).
  Later visits are fast. Your data is kept in Neon, so users and transactions persist.
  Tip: the dependencies are about 365 MB; Vercel's limit is 500 MB, so do not add more big libraries.

SETTINGS (environment variables, all optional)
  SECRET_KEY=...            fixed session key (otherwise secret.key is generated)
  SHOW_DEMO_ACCOUNT=0       hide/disable the demo account when you go public
  HTTPS_ONLY=1              mark cookies Secure once your site uses https
  FINTRACK_DB=/path/x.db    where to keep the SQLite database (local use)
  DATABASE_URL=postgresql://...  use Postgres instead of SQLite (needed on Vercel)

FILES
  app.py (website, login, database) | ml.py (models) | demo_data.py | charts.py
  templates.py (pages) | requirements.txt | Procfile | vercel.json
