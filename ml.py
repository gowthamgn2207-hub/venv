"""
ml.py - the machine-learning engine of FinTrack.

These are the same algorithms as the original project slides:
  * TF-IDF + Multinomial Naive Bayes  -> expense categorization
  * Random Forest Regression          -> next-month expense forecast
  * K-Means clustering                -> spending behaviour (Lean / Balanced / High-spend)
  * Rules layer on top of the ML      -> alerts and saving tips

Everything is trained on the signed-in user's OWN transactions, on the fly.
When a user does not have enough history for a model, the function says so
and falls back to a simpler method instead of pretending.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_absolute_error, r2_score, silhouette_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

EXP_CATS = ["Food", "Travel", "Shopping", "Bills", "Education",
            "Entertainment", "Healthcare", "Housing", "Other"]

# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def shift_month(ym, delta):
    y, m = int(ym[:4]), int(ym[5:7])
    t = y * 12 + (m - 1) + delta
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def month_range(first, last):
    out, m = [], first
    while m <= last:
        out.append(m)
        m = shift_month(m, 1)
    return out


def monthly_matrix(tx, cur):
    """Complete months (before the current, still-running month) x categories,
    filled with zeros where nothing was spent. Returns None if no history."""
    exp = [t for t in tx if t["kind"] == "expense" and t["date"][:7] < cur]
    if not exp:
        return None
    first, last = min(t["date"][:7] for t in exp), shift_month(cur, -1)
    months = month_range(first, last)
    mat = pd.DataFrame(0.0, index=months, columns=EXP_CATS)
    for t in exp:
        cat = t["category"] if t["category"] in EXP_CATS else "Other"
        mat.loc[t["date"][:7], cat] += float(t["amount"])
    return mat


# ----------------------------------------------------------------------
# 1. Expense categorizer: TF-IDF + Naive Bayes
# ----------------------------------------------------------------------

SEED = {
    "Food": ["swiggy", "zomato", "dominos pizza", "campus canteen", "local cafe", "restaurant dinner",
             "lunch", "breakfast", "grocery store", "coffee", "food order", "bigbasket", "kfc", "biryani"],
    "Travel": ["uber", "ola cab", "metro card recharge", "petrol pump", "bus pass", "bus ticket",
               "train ticket irctc", "taxi", "auto rickshaw", "fuel", "rapido", "flight ticket"],
    "Shopping": ["amazon", "flipkart", "myntra", "local mall", "decathlon", "shirt", "shoes", "dress",
                 "shopping", "meesho"],
    "Bills": ["electricity board", "electricity bill", "airtel postpaid", "jio recharge", "water bill",
              "mobile bill", "wifi broadband", "internet bill", "gas cylinder", "dth recharge"],
    "Education": ["udemy", "book store", "stationery", "coaching fee", "college fee", "tuition",
                  "exam fee", "course", "coursera", "library"],
    "Entertainment": ["netflix", "bookmyshow", "spotify", "pvr cinemas", "movie", "gaming", "game",
                      "hotstar", "prime video", "concert"],
    "Healthcare": ["apollo pharmacy", "clinic visit", "gym membership", "hospital", "doctor", "medicine",
                   "pharmacy", "medplus", "dental", "lab test"],
    "Housing": ["hostel fee", "pg rent", "house rent", "rent", "maintenance", "society maintenance",
                "landlord"],
    "Other": ["miscellaneous", "gift", "donation", "atm withdrawal", "transfer"],
}

_seed_model = None


def _fit(rows):
    docs = [d for d, _ in rows]
    labels = [c for _, c in rows]
    model = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2))),
        ("clf", MultinomialNB(alpha=0.3)),
    ])
    model.fit(docs, labels)
    return model


def _seed_rows():
    rows = []
    for cat, phrases in SEED.items():
        for p in phrases:
            rows += [(p, cat)] * 3
    return rows


def categorize(description, kind, user_rows=()):
    """Return (category, explanation). user_rows = [(description, category), ...]
    from the user's own history, so the model learns their habits."""
    text = (description or "").strip().lower()
    if kind == "income":
        if any(w in text for w in ("salary", "payroll", "wage", "stipend")):
            return "Salary", "income keyword"
        return "Other", "income"
    if not text:
        return "Other", "no description"

    global _seed_model
    own = [(d.lower(), c) for d, c in user_rows if d and c in EXP_CATS]
    if own:
        model = _fit(_seed_rows() + own * 3)
        source = "Naive Bayes trained on your history"
    else:
        if _seed_model is None:
            _seed_model = _fit(_seed_rows())
        model, source = _seed_model, "Naive Bayes"

    if model.named_steps["tfidf"].transform([text]).nnz == 0:
        return "Other", "no recognised words"
    proba = model.predict_proba([text])[0]
    i = int(np.argmax(proba))
    return str(model.classes_[i]), f"{source}, {proba[i]:.0%} confidence"


# ----------------------------------------------------------------------
# 2. Forecast: Random Forest Regression (with an honest fallback)
# ----------------------------------------------------------------------

FEATURES = ["lag_1", "lag_2", "lag_3", "rolling_avg_3", "month_num"]


def _build_rows(mat):
    months = list(mat.index)
    rows = []
    for cat in mat.columns:
        s = mat[cat].values
        if s.sum() == 0:
            continue
        for i in range(3, len(months)):
            rows.append({
                "month": months[i], "category": cat, "y": s[i],
                "lag_1": s[i - 1], "lag_2": s[i - 2], "lag_3": s[i - 3],
                "rolling_avg_3": float(np.mean(s[i - 3:i])),
                "month_num": int(months[i][5:7]),
            })
    return pd.DataFrame(rows)


def _matrix(df):
    X = df[FEATURES].copy()
    for c in EXP_CATS:
        X["cat_" + c] = (df["category"] == c).astype(int)
    return X


def _wavg(values):
    w = [0.5, 0.3, 0.2][: len(values)]
    return float(np.dot(values, w) / sum(w))


def forecast(tx, cur):
    """Forecast the full-month spend for `cur` (the month after the last complete month)."""
    mat = monthly_matrix(tx, cur)
    base = {"target": cur, "per_category": [], "total": 0.0, "history": [],
            "metrics": None, "importances": [], "n_months": 0, "n_rows": 0}
    if mat is None:
        return {**base, "method": "none", "method_label": "No forecast yet",
                "note": "Forecasts use complete past months. Add expenses from at least one earlier month, "
                        "or load the demo data to see the models working."}

    totals = mat.sum(axis=1)
    base["history"] = [(m, float(v)) for m, v in totals.items()][-12:]
    base["n_months"] = len(mat)
    last_actual = mat.iloc[-1]
    active = [c for c in mat.columns if mat[c].sum() > 0]

    df = _build_rows(mat)
    base["n_rows"] = len(df)
    months = list(mat.index)

    # ---- Random Forest when there is enough history ----
    if len(mat) >= 9 and len(df) >= 30:
        test_months = months[-3:]
        train, test = df[~df["month"].isin(test_months)], df[df["month"].isin(test_months)]
        metrics = None
        if len(train) >= 12 and len(test) >= 3:
            probe = RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=2,
                                          random_state=42).fit(_matrix(train), train["y"])
            pred = probe.predict(_matrix(test))
            metrics = {
                "mae": float(mean_absolute_error(test["y"], pred)),
                "naive_mae": float(mean_absolute_error(test["y"], test["lag_1"])),
                "r2": float(r2_score(test["y"], pred)),
                "holdout_months": len(test_months),
                "train_rows": int(len(train)),
            }
        model = RandomForestRegressor(n_estimators=300, max_depth=8, min_samples_leaf=2,
                                      random_state=42).fit(_matrix(df), df["y"])
        per = []
        for cat in active:
            s = mat[cat].values
            row = pd.DataFrame([{
                "lag_1": s[-1], "lag_2": s[-2], "lag_3": s[-3],
                "rolling_avg_3": float(np.mean(s[-3:])), "month_num": int(cur[5:7]),
                "category": cat,
            }])
            p = max(0.0, float(model.predict(_matrix(row))[0]))
            per.append({"category": cat, "predicted": round(p, 2), "last_month": round(float(last_actual[cat]), 2)})
        per.sort(key=lambda r: -r["predicted"])
        names = _matrix(df).columns
        imp = sorted(zip(names, model.feature_importances_), key=lambda x: -x[1])[:5]
        return {**base, "method": "random_forest", "method_label": "Random Forest Regression",
                "per_category": per, "total": round(sum(r["predicted"] for r in per), 2),
                "metrics": metrics, "importances": [(n, float(v)) for n, v in imp],
                "note": "Trained on your own monthly spending per category (last 1-3 months, rolling average, "
                        "calendar month and category)."}

    # ---- weighted moving average fallback ----
    per = []
    for cat in active:
        recent = list(mat[cat].values[-3:][::-1])
        per.append({"category": cat, "predicted": round(_wavg(recent), 2),
                    "last_month": round(float(last_actual[cat]), 2)})
    per.sort(key=lambda r: -r["predicted"])
    return {**base, "method": "weighted_average", "method_label": "Weighted moving average (fallback)",
            "per_category": per, "total": round(sum(r["predicted"] for r in per), 2),
            "note": f"The Random Forest needs about 9 complete months of history (you have {len(mat)}). "
                    "Until then this uses a weighted average of the last 3 months (50% / 30% / 20%). "
                    "Load the demo data to see the Random Forest."}


# ----------------------------------------------------------------------
# 3. Behaviour clusters: K-Means
# ----------------------------------------------------------------------

def behaviour(tx, cur):
    """K-Means on the monthly spending pattern (amount per category).
    Raw rupee amounts are used so clusters reflect how MUCH was spent, not just noise in
    small categories. k (2 or 3) is picked by silhouette score. If the clusters barely differ
    in total spend, we say the user's spending is steady instead of inventing labels."""
    mat = monthly_matrix(tx, cur)
    if mat is None or len(mat) < 6:
        have = 0 if mat is None else len(mat)
        return {"available": False,
                "reason": f"K-Means needs at least 6 complete months of expenses (you have {have})."}
    X = mat[EXP_CATS].values
    totals = mat.sum(axis=1).values
    best = None
    for k in ((2, 3) if len(mat) >= 9 else (2,)):
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        if len(set(km.labels_)) < k:
            continue
        sil = silhouette_score(X, km.labels_)
        if best is None or sil > best[0] + 0.02:      # prefer fewer clusters unless clearly better
            best = (sil, k, km)
    sil, k, km = best
    order = pd.Series(totals).groupby(km.labels_).mean().sort_values().index
    lo, hi = float(pd.Series(totals).groupby(km.labels_).mean().min()), float(pd.Series(totals).groupby(km.labels_).mean().max())
    if lo > 0 and (hi - lo) / lo < 0.05:
        return {"available": False, "steady": True,
                "reason": "K-Means found no meaningful difference between your months: your spending is steady."}
    names = ["Lean", "Balanced", "High-spend"] if k == 3 else ["Lean", "High-spend"]
    name_map = {int(cid): names[i] for i, cid in enumerate(order)}
    labels = [name_map[int(l)] for l in km.labels_]
    timeline = [{"month": m, "total": float(t), "label": l} for m, t, l in zip(mat.index, totals, labels)]
    summary = []
    for n in names:
        idx = [i for i, l in enumerate(labels) if l == n]
        if not idx:
            continue
        sub = mat.iloc[idx]
        summary.append({"label": n, "months": len(idx), "avg_total": float(sub.sum(axis=1).mean()),
                        "top_category": str(sub.drop(columns=["Housing"], errors="ignore").mean().idxmax())})
    return {"available": True, "k": k, "silhouette": float(sil), "timeline": timeline, "summary": summary,
            "latest": timeline[-1]["label"], "latest_month": timeline[-1]["month"]}


# ----------------------------------------------------------------------
# 4. Recommendation engine (rules on top of the ML output)
# ----------------------------------------------------------------------

def recommendations(fc, spent, budgets, beh, income, expenses):
    """spent = this month's spend so far per category; budgets = {category: limit}."""
    out = []
    for cat, lim in sorted(budgets.items()):
        if lim <= 0:
            continue
        used = spent.get(cat, 0.0)
        if used >= lim:
            out.append(("danger", f"You have already reached your {cat} budget this month "
                                  f"({used:,.0f} of {lim:,.0f})."))
        elif used >= 0.8 * lim:
            out.append(("warn", f"You have used {used / lim:.0%} of your {cat} budget this month."))
    for r in fc.get("per_category", []):
        lim = budgets.get(r["category"], 0)
        if lim > 0 and r["predicted"] > lim:
            out.append(("warn", f"{r['category']} is forecast at {r['predicted']:,.0f} for "
                                f"{fc['target']}, which is {r['predicted'] - lim:,.0f} over your budget of {lim:,.0f}."))
        if r["last_month"] > 0 and r["predicted"] > r["last_month"] * 1.2 and r["predicted"] - r["last_month"] > 200:
            out.append(("tip", f"{r['category']} spending is trending up "
                               f"({r['last_month']:,.0f} last month, {r['predicted']:,.0f} forecast). "
                               "Consider a stricter cap."))
    if spent:
        top = max(spent, key=spent.get)
        out.append(("info", f"Your highest-spending category this month so far is {top} ({spent[top]:,.0f})."))
    if income > 0:
        rate = (income - expenses) / income
        if rate < 0.2:
            out.append(("tip", f"Your savings rate this month is {rate:.0%}. A common target is at least 20% of income."))
        else:
            out.append(("good", f"Your savings rate this month is {rate:.0%}, above the common 20% target."))
    if beh.get("available"):
        if beh["latest"] == "High-spend":
            out.append(("warn", f"Your last complete month ({beh['latest_month']}) was a high-spend month "
                                "compared with your usual pattern."))
        elif beh["latest"] == "Lean":
            out.append(("good", f"Your last complete month ({beh['latest_month']}) was one of your leanest. "
                                "Consider moving the surplus into savings."))
    if not out:
        out.append(("info", "Add transactions and budgets to receive recommendations."))
    return out
