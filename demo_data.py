"""Generates 24 months of realistic sample transactions so the ML models have history to learn from."""

import numpy as np
from datetime import date

from ml import shift_month

# monthly base spend, noise, how strongly festive months push it up
CATEGORIES = {
    "Food":          (4500, 600, 0.3),
    "Travel":        (2200, 350, 0.1),
    "Shopping":      (3200, 800, 0.9),
    "Bills":         (2000, 200, 0.1),
    "Education":     (1500, 250, 0.1),
    "Entertainment": (1800, 450, 0.7),
    "Healthcare":    (1200, 350, 0.1),
}
DESCRIPTIONS = {
    "Food": ["Swiggy order", "Zomato dinner", "Campus canteen lunch", "Dominos pizza", "Coffee at local cafe", "Grocery store"],
    "Travel": ["Uber ride", "Ola cab", "Metro card recharge", "Petrol pump", "Bus pass"],
    "Shopping": ["Amazon order", "Flipkart purchase", "Myntra shirt", "Decathlon shoes", "Local mall"],
    "Bills": ["Electricity bill", "Airtel postpaid bill", "Jio recharge", "Water bill", "Wifi broadband"],
    "Education": ["Udemy course", "Book store", "Stationery", "Coaching fee"],
    "Entertainment": ["Netflix subscription", "BookMyShow movie", "Spotify", "PVR cinemas", "Gaming"],
    "Healthcare": ["Apollo pharmacy", "Clinic visit", "Gym membership", "Medicine"],
}
FESTIVE = {10: 1.35, 11: 1.25, 12: 1.2, 1: 1.1}
PAYMENTS = ["UPI", "UPI", "Card", "Cash", "Bank Transfer"]


def generate(today=None, months=24, seed=42):
    """Return a list of transaction dicts for the `months` complete months before today's month,
    plus a partial current month."""
    today = today or date.today()
    cur = f"{today.year:04d}-{today.month:02d}"
    rng = np.random.RandomState(seed)
    rows = []

    def add(kind, amount, category, desc, day, ym):
        rows.append({"kind": kind, "amount": round(float(amount), 2), "category": category,
                     "description": desc, "payment": str(rng.choice(PAYMENTS)),
                     "date": f"{ym}-{day:02d}"})

    for i in range(months, -1, -1):
        ym = shift_month(cur, -i)
        is_current = ym == cur
        max_day = max(1, min(28, today.day)) if is_current else 28
        if is_current and today.day < 3:
            continue
        drift = 1.0 + 0.15 * (months - i) / months
        frac = max_day / 28.0 if is_current else 1.0
        boost = FESTIVE.get(int(ym[5:7]), 1.0)

        add("income", 55000, "Salary", "Monthly salary", 1, ym)
        add("expense", 8000, "Housing", "Hostel fee / PG rent", min(2, max_day), ym)

        for cat, (base, noise, sens) in CATEGORIES.items():
            total = max(0.0, rng.normal(base * (1 + (boost - 1) * sens) * drift, noise)) * frac
            n = int(rng.randint(3, 9)) if not is_current else max(1, int(rng.randint(2, 5)))
            for part in rng.dirichlet(np.ones(n)) * total:
                add("expense", part, cat, str(rng.choice(DESCRIPTIONS[cat])), int(rng.randint(1, max_day + 1)), ym)
    return rows
