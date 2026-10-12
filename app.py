"""
FinTrack - AI-Based Personal Finance Management and Expense Forecasting
Flask website with login, SQLite database and the real ML models (see ml.py).

Run:  python app.py        (opens http://127.0.0.1:5000)
"""

import hmac
import math
import os
import secrets
import sqlite3
import threading
import webbrowser
from contextlib import contextmanager
from datetime import date, datetime

from flask import (Flask, abort, flash, g, has_request_context, jsonify, redirect, render_template, request,
                   session, url_for)
from jinja2 import DictLoader
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash

import charts
import demo_data
import ml
import templates as T

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("FINTRACK_DB", os.path.join(BASE_DIR, "fintrack.db"))
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@fintrack.app")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Demo@1234")
SHOW_DEMO = os.environ.get("SHOW_DEMO_ACCOUNT", "1") == "1"

PAYMENTS = ["Cash", "UPI", "Card", "Bank Transfer", "Other"]
INC_CATS = ["Salary", "Scholarship", "Freelance", "Gift", "Other"]
EXP_CATS = ml.EXP_CATS
NAV = [("dashboard", "Dashboard"), ("transactions", "Transactions"), ("add_transaction", "Add"),
       ("budgets", "Budgets"), ("forecast_page", "Forecast"), ("insights", "Insights")]

app = Flask(__name__)
app.jinja_loader = DictLoader({"base.html": T.BASE, "auth.html": T.AUTH, "dash.html": T.DASH, "add.html": T.ADD,
                               "tx.html": T.TX, "bud.html": T.BUD, "fc.html": T.FC, "ins.html": T.INS})
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("HTTPS_ONLY", "0") == "1")


CONFIG_PROBLEMS = []


def _secret():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    if os.environ.get("VERCEL"):
        CONFIG_PROBLEMS.append("SECRET_KEY is missing. In Vercel open Project > Settings > Environment Variables, add "
                               "SECRET_KEY (any long random text), then redeploy.")
        return secrets.token_hex(32)
    path = os.path.join(BASE_DIR, "secret.key")
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        key = secrets.token_hex(32)
        try:
            with open(path, "w") as f:
                f.write(key)
        except OSError:
            pass
        return key


app.secret_key = _secret()


# ----------------------------------------------------------------------
# database: SQLite on your own computer, Postgres when DATABASE_URL is set (Vercel)
# ----------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
USE_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
if USE_PG and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
if os.environ.get("VERCEL") and not USE_PG:
    CONFIG_PROBLEMS.append("No database is connected (DATABASE_URL is missing). In Vercel open your project > Storage, "
                           "create a Neon database and click Connect Project, then Redeploy.")
if USE_PG:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityErrors = (sqlite3.IntegrityError, psycopg.errors.IntegrityError)
else:
    IntegrityErrors = (sqlite3.IntegrityError,)


class _PGCursor:
    """Makes a psycopg cursor look like the sqlite3 one the rest of the app uses."""

    def __init__(self, cur, lastrowid=None):
        self._c, self.lastrowid = cur, lastrowid

    def fetchone(self):
        return self._c.fetchone() if self._c.description else None

    def fetchall(self):
        return self._c.fetchall() if self._c.description else []

    def __iter__(self):
        return iter(self.fetchall())


class _PGConn:
    def __init__(self):
        self.raw = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=15,
                                  prepare_threshold=None)  # safe behind Neon's connection pooler

    def execute(self, sql, params=()):
        sql = sql.replace("?", "%s")
        want_id = sql.lstrip().upper().startswith("INSERT INTO") and "RETURNING" not in sql.upper() \
            and ("INTO USERS" in sql.upper() or "INTO TRANSACTIONS" in sql.upper())
        if want_id:
            sql += " RETURNING id"
        cur = self.raw.execute(sql, params)
        return _PGCursor(cur, cur.fetchone()["id"] if want_id else None)

    def executemany(self, sql, rows):
        with self.raw.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), rows)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def _open():
    if USE_PG:
        return _PGConn()
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def db():
    """Inside a web request every call shares one connection (closed when the request ends);
    outside a request (start-up) it opens and closes its own."""
    shared = has_request_context()
    if shared:
        con = getattr(g, "_con", None)
        if con is None:
            con = g._con = _open()
    else:
        con = _open()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        if not shared:
            con.close()


@app.teardown_appcontext
def _close_con(_exc):
    con = g.pop("_con", None)
    if con is not None:
        con.close()


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
    pw TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL CHECK(kind IN ('income','expense')), amount REAL NOT NULL CHECK(amount>0),
    category TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', payment TEXT NOT NULL DEFAULT 'Other',
    date TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_tx_user_date ON transactions(user_id, date);
CREATE TABLE IF NOT EXISTS budgets(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
    category TEXT NOT NULL, month TEXT NOT NULL, amount REAL NOT NULL CHECK(amount>0),
    is_demo INTEGER NOT NULL DEFAULT 0, UNIQUE(user_id, category, month));
"""
SCHEMA_PG = [
    "CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, "
    "pw TEXT NOT NULL, created TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS transactions(id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), "
    "kind TEXT NOT NULL CHECK(kind IN ('income','expense')), amount DOUBLE PRECISION NOT NULL CHECK(amount>0), "
    "category TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', payment TEXT NOT NULL DEFAULT 'Other', "
    "date TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 0)",
    "CREATE INDEX IF NOT EXISTS ix_tx_user_date ON transactions(user_id, date)",
    "CREATE TABLE IF NOT EXISTS budgets(id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), "
    "category TEXT NOT NULL, month TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL CHECK(amount>0), "
    "is_demo INTEGER NOT NULL DEFAULT 0, UNIQUE(user_id, category, month))",
]


def init_db():
    with db() as con:
        if USE_PG:
            for stmt in SCHEMA_PG:
                con.execute(stmt)
            return
        con.executescript(SCHEMA_SQLITE)
        # migration for databases created before is_demo existed
        for table in ("transactions", "budgets"):
            cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]
            if "is_demo" not in cols:
                con.execute(f"ALTER TABLE {table} ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0")


def load_demo(con, uid):
    today = date.today()
    cur = today.strftime("%Y-%m")
    if con.execute("SELECT 1 FROM transactions WHERE user_id=? AND is_demo=1", (uid,)).fetchone():
        return False
    con.executemany(
        "INSERT INTO transactions(user_id,kind,amount,category,description,payment,date,is_demo) VALUES(?,?,?,?,?,?,?,1)",
        [(uid, r["kind"], r["amount"], r["category"], r["description"], r["payment"], r["date"])
         for r in demo_data.generate(today)])
    for cat, amt in (("Food", 5500), ("Shopping", 3500), ("Entertainment", 2200), ("Travel", 2500)):
        con.execute("INSERT INTO budgets(user_id,category,month,amount,is_demo) VALUES(?,?,?,?,1) "
                    "ON CONFLICT(user_id,category,month) DO NOTHING", (uid, cat, cur, amt))
    return True


def seed_demo_account():
    if not SHOW_DEMO:
        return
    with db() as con:
        row = con.execute("SELECT id FROM users WHERE email=?", (DEMO_EMAIL,)).fetchone()
        if row:
            return
        try:
            cur = con.execute("INSERT INTO users(name,email,pw,created) VALUES(?,?,?,?)",
                              ("Demo Student", DEMO_EMAIL, generate_password_hash(DEMO_PASSWORD), datetime.now().isoformat()))
            load_demo(con, cur.lastrowid)
        except IntegrityErrors:
            pass  # another instance created it first


# ----------------------------------------------------------------------
# security: login + CSRF
# ----------------------------------------------------------------------
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.before_request
def protect():
    g.user = None
    problem = ensure_ready()
    if problem:
        return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                f"<body style='font-family:system-ui;max-width:640px;margin:8vh auto;padding:0 16px'>"
                f"<h2>FinTrack is not set up yet</h2><p>{escape(problem)}</p>"
                f"<p style='color:#6b7280'>Fix this in your hosting settings and reload the page.</p></body>", 503)
    uid = session.get("uid")
    if uid:
        with db() as con:
            g.user = con.execute("SELECT id,name,email FROM users WHERE id=?", (uid,)).fetchone()
        if g.user is None:
            session.clear()
    if request.method == "POST":
        sent = request.form.get("csrf") or request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(str(sent), str(session.get("csrf", ""))) or not session.get("csrf"):
            abort(400, "Security token missing or expired. Go back, refresh the page and try again.")


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*a, **kw):
        if g.user is None:
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper


@app.after_request
def headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(400)
def bad_request(e):
    return f"<h2>Request blocked</h2><p>{e.description}</p><p><a href='/'>Back to FinTrack</a></p>", 400


# ----------------------------------------------------------------------
# template helpers
# ----------------------------------------------------------------------
def inr_fmt(v):
    v = float(v or 0)
    neg = v < 0
    v = abs(v)
    s = f"{v:.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    out = whole if frac == "00" else f"{whole}.{frac}"
    return ("-" if neg else "") + out


app.jinja_env.filters["inr"] = inr_fmt


@app.context_processor
def inject():
    return {"csrf_token": csrf_token, "user": g.get("user"), "NAV": NAV}


def month_name(ym):
    return datetime.strptime(ym + "-01", "%Y-%m-%d").strftime("%B %Y")


def user_tx(uid):
    with db() as con:
        return [dict(r) for r in con.execute(
            "SELECT id,kind,amount,category,description,payment,date FROM transactions WHERE user_id=? ORDER BY date DESC,id DESC", (uid,))]


# forecast results are cached per user until their data changes (training a forest is not free)
_cache, _lock = {}, threading.Lock()


def ml_bundle(uid, tx, cur):
    sig = (cur, len(tx), tx[0]["id"] if tx else 0, round(sum(t["amount"] for t in tx), 2))
    with _lock:
        hit = _cache.get(uid)
        if hit and hit[0] == sig:
            return hit[1]
    fc = ml.forecast(tx, cur)
    beh = ml.behaviour(tx, cur)
    with _lock:
        if len(_cache) > 200:
            _cache.clear()
        _cache[uid] = (sig, (fc, beh))
    return fc, beh


# ----------------------------------------------------------------------
# auth routes
# ----------------------------------------------------------------------
def valid_email(e):
    return 3 <= len(e) <= 120 and "@" in e and "." in e.split("@")[-1] and " " not in e


@app.route("/")
def home():
    return redirect(url_for("dashboard" if g.user else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:60]
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        err = None
        if not name:
            err = "Please enter your name."
        elif not valid_email(email):
            err = "Please enter a valid email address."
        elif len(pw) < 8:
            err = "Password must be at least 8 characters."
        if not err:
            try:
                with db() as con:
                    cur = con.execute("INSERT INTO users(name,email,pw,created) VALUES(?,?,?,?)",
                                      (name, email, generate_password_hash(pw), datetime.now().isoformat()))
                    uid = cur.lastrowid
                session.clear()
                session["uid"] = uid
                flash("Welcome to FinTrack! Add a transaction, or load sample data from the dashboard.", "ok")
                return redirect(url_for("dashboard"))
            except IntegrityErrors:
                err = "That email is already registered. Try logging in."
        flash(err, "error")
    return render_template("auth.html", heading="Create account", register=True, form=request.form, demo_email=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        with db() as con:
            u = con.execute("SELECT id,pw FROM users WHERE email=?", (email,)).fetchone()
        if u and check_password_hash(u["pw"], request.form.get("password", "")):
            session.clear()
            session["uid"] = u["id"]
            return redirect(url_for("dashboard"))
        flash("Wrong email or password.", "error")
    return render_template("auth.html", heading="Log in", register=False, form=request.form,
                           demo_email=DEMO_EMAIL if SHOW_DEMO else None, demo_password=DEMO_PASSWORD)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ----------------------------------------------------------------------
# app pages
# ----------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    cur = date.today().strftime("%Y-%m")
    tx = user_tx(g.user["id"])
    inc = sum(t["amount"] for t in tx if t["kind"] == "income" and t["date"][:7] == cur)
    exp = sum(t["amount"] for t in tx if t["kind"] == "expense" and t["date"][:7] == cur)
    by_cat = {}
    for t in tx:
        if t["kind"] == "expense" and t["date"][:7] == cur:
            by_cat[t["category"]] = by_cat.get(t["category"], 0) + t["amount"]
    bars = []
    for i in range(5, -1, -1):
        m = ml.shift_month(cur, -i)
        v = sum(t["amount"] for t in tx if t["kind"] == "expense" and t["date"][:7] == m)
        bars.append((charts._mlabel(m), v, "#315fe8" if m != cur else "#93a9f5"))
    fc, _ = ml_bundle(g.user["id"], tx, cur)
    return render_template("dash.html", income=inc, expenses=exp, remaining=inc - exp, fc=fc,
                           month_name=month_name(cur), has_data=bool(tx),
                           donut=charts.donut(list(by_cat.items())), bars=charts.bar_chart(bars, "Expenses, last 6 months"))


def parse_amount(raw):
    try:
        v = float(str(raw).replace(",", "").strip())
    except ValueError:
        return None
    return round(v, 2) if math.isfinite(v) and 0 < v < 1e9 else None


@app.route("/transaction/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    today = date.today().isoformat()
    if request.method == "POST":
        f = request.form
        kind = f.get("kind") if f.get("kind") in ("income", "expense") else "expense"
        amount = parse_amount(f.get("amount"))
        desc = f.get("description", "").strip()[:120]
        try:
            d = datetime.strptime(f.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            d = None
        payment = f.get("payment") if f.get("payment") in PAYMENTS else "Other"
        if amount is None or d is None or d > date.today():
            flash("Enter an amount above 0 and a valid date that is not in the future.", "error")
        else:
            cats = EXP_CATS if kind == "expense" else INC_CATS
            cat = f.get("category", "auto")
            if cat == "auto" or cat not in cats:
                hist = [(t["description"], t["category"]) for t in user_tx(g.user["id"])[:600]
                        if t["kind"] == "expense"]
                cat, _ = ml.categorize(desc, kind, hist)
            with db() as con:
                con.execute("INSERT INTO transactions(user_id,kind,amount,category,description,payment,date) VALUES(?,?,?,?,?,?,?)",
                            (g.user["id"], kind, amount, cat, desc, payment, d.isoformat()))
            flash(f"Saved {kind} of ₹{inr_fmt(amount)} under {cat}.", "ok")
            return redirect(url_for("transactions"))
    return render_template("add.html", today=today, payments=PAYMENTS, exp_cats=EXP_CATS, inc_cats=INC_CATS)


@app.route("/api/categorize", methods=["POST"])
@login_required
def api_categorize():
    data = request.get_json(silent=True) or {}
    kind = data.get("kind") if data.get("kind") in ("income", "expense") else "expense"
    hist = [(t["description"], t["category"]) for t in user_tx(g.user["id"])[:600] if t["kind"] == "expense"]
    cat, why = ml.categorize(str(data.get("description", ""))[:120], kind, hist)
    return jsonify(category=cat, explanation=why)


@app.route("/transactions")
@login_required
def transactions():
    q = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "")
    month = request.args.get("month", "")
    rows = [t for t in user_tx(g.user["id"])
            if (not q or q in t["description"].lower() or q in t["category"].lower())
            and (not category or t["category"] == category) and (not month or t["date"][:7] == month)]
    return render_template("tx.html", rows=rows[:300], capped=len(rows) > 300, q=q, category=category, month=month,
                           cats=EXP_CATS + [c for c in INC_CATS if c not in EXP_CATS])


@app.route("/transaction/<int:tid>/delete", methods=["POST"])
@login_required
def delete_transaction(tid):
    with db() as con:
        con.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tid, g.user["id"]))
    flash("Transaction deleted.", "ok")
    return redirect(request.referrer or url_for("transactions"))


@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    cur = date.today().strftime("%Y-%m")
    uid = g.user["id"]
    if request.method == "POST":
        cat, amt = request.form.get("category"), parse_amount(request.form.get("amount"))
        if cat in EXP_CATS and amt:
            with db() as con:
                con.execute("INSERT INTO budgets(user_id,category,month,amount,is_demo) VALUES(?,?,?,?,0) "
                            "ON CONFLICT(user_id,category,month) DO UPDATE SET amount=excluded.amount, is_demo=0",
                            (uid, cat, cur, amt))
            flash(f"{cat} budget saved.", "ok")
        else:
            flash("Choose a category and enter an amount above 0.", "error")
        return redirect(url_for("budgets"))
    spent = {}
    for t in user_tx(uid):
        if t["kind"] == "expense" and t["date"][:7] == cur:
            spent[t["category"]] = spent.get(t["category"], 0) + t["amount"]
    with db() as con:
        rows = con.execute("SELECT id,category,amount FROM budgets WHERE user_id=? AND month=? ORDER BY category", (uid, cur)).fetchall()
    items = [{"id": r["id"], "category": r["category"], "amount": r["amount"], "spent": spent.get(r["category"], 0),
              "left": r["amount"] - spent.get(r["category"], 0), "pct": spent.get(r["category"], 0) / r["amount"] * 100} for r in rows]
    return render_template("bud.html", items=items, exp_cats=EXP_CATS, month_name=month_name(cur))


@app.route("/budget/<int:bid>/delete", methods=["POST"])
@login_required
def delete_budget(bid):
    with db() as con:
        con.execute("DELETE FROM budgets WHERE id=? AND user_id=?", (bid, g.user["id"]))
    return redirect(url_for("budgets"))


@app.route("/forecast")
@login_required
def forecast_page():
    cur = date.today().strftime("%Y-%m")
    tx = user_tx(g.user["id"])
    fc, _ = ml_bundle(g.user["id"], tx, cur)
    hist = fc["history"][-8:]
    chart = charts.line_chart(hist, (fc["target"], fc["total"]) if fc["total"] else None) if hist else ""
    return render_template("fc.html", fc=fc, chart=chart, last_total=hist[-1][1] if hist else 0)


@app.route("/insights")
@login_required
def insights():
    cur = date.today().strftime("%Y-%m")
    tx = user_tx(g.user["id"])
    fc, beh = ml_bundle(g.user["id"], tx, cur)
    spent, inc, exp = {}, 0.0, 0.0
    for t in tx:
        if t["date"][:7] != cur:
            continue
        if t["kind"] == "expense":
            spent[t["category"]] = spent.get(t["category"], 0) + t["amount"]
            exp += t["amount"]
        else:
            inc += t["amount"]
    with db() as con:
        bud = {r["category"]: r["amount"] for r in con.execute(
            "SELECT category,amount FROM budgets WHERE user_id=? AND month=?", (g.user["id"], cur))}
    recs = ml.recommendations(fc, spent, bud, beh, inc, exp)
    chart = ""
    if beh.get("available"):
        chart = charts.bar_chart([(charts._mlabel(r["month"]), r["total"], charts.LABEL_COLORS[r["label"]])
                                  for r in beh["timeline"][-12:]], "Monthly spend coloured by K-Means cluster")
    return render_template("ins.html", recs=recs, beh=beh, chart=chart, colors=charts.LABEL_COLORS)


@app.route("/demo/load", methods=["POST"])
@login_required
def demo_load():
    with db() as con:
        added = load_demo(con, g.user["id"])
    flash("Sample data loaded: 24 months of transactions." if added else "Sample data is already loaded.", "ok")
    return redirect(url_for("dashboard"))


@app.route("/demo/clear", methods=["POST"])
@login_required
def demo_clear():
    with db() as con:
        con.execute("DELETE FROM transactions WHERE user_id=? AND is_demo=1", (g.user["id"],))
        con.execute("DELETE FROM budgets WHERE user_id=? AND is_demo=1", (g.user["id"],))
    flash("Sample data removed. Your own entries were kept.", "ok")
    return redirect(url_for("dashboard"))


_ready, _ready_lock, _last_error = False, threading.Lock(), None


def ensure_ready():
    """Create tables + demo account once per server instance. Returns an error text, or None when ready."""
    global _ready, _last_error
    if CONFIG_PROBLEMS:
        return " ".join(CONFIG_PROBLEMS)
    if _ready:
        return None
    with _ready_lock:
        if _ready:
            return None
        try:
            init_db()
            seed_demo_account()
            _ready, _last_error = True, None
        except Exception as e:  # shown on screen so the cause can be fixed without digging through logs
            _last_error = f"Could not start the database: {type(e).__name__}: {str(e)[:300]}"
            app.logger.exception("startup failed")
    return None if _ready else _last_error

if __name__ == "__main__":
    err = ensure_ready()
    if err:
        raise SystemExit(err)
    port = int(os.environ.get("PORT", 5000))
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, debug=False)
