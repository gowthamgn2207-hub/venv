"""Tiny server-side SVG charts, so the site needs no JavaScript chart library or CDN."""

from markupsafe import Markup, escape

PALETTE = ["#315fe8", "#16a37f", "#f59e0b", "#ef4444", "#8b5cf6", "#0ea5e9", "#ec4899", "#64748b", "#84cc16"]
LABEL_COLORS = {"Lean": "#16a37f", "Balanced": "#f59e0b", "High-spend": "#ef4444"}


def _short(v):
    v = float(v)
    if abs(v) >= 100000:
        return f"{v / 100000:.1f}L"
    if abs(v) >= 1000:
        return f"{v / 1000:.0f}k"
    return f"{v:.0f}"


def _mlabel(ym):
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{names[int(ym[5:7]) - 1]} {ym[2:4]}"


def _frame(w, h, body, label):
    return Markup(f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="{escape(label)}">{body}</svg>')


def _grid(w, h, left, top, bottom, vmax):
    out = []
    for i in range(5):
        y = top + (h - top - bottom) * i / 4
        val = vmax * (1 - i / 4)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{w - 10}" y2="{y:.1f}" stroke="#e5e8f0"/>'
                   f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{_short(val)}</text>')
    return "".join(out)


def bar_chart(items, label="Bar chart", w=640, h=240):
    """items = [(label, value, colour_or_None)]"""
    if not items or max(v for _, v, _ in items) <= 0:
        return Markup('<p class="muted">No data to chart yet.</p>')
    left, top, bottom = 46, 14, 34
    vmax = max(v for _, v, _ in items) * 1.1
    bw = (w - left - 10) / len(items)
    body = [_grid(w, h, left, top, bottom, vmax)]
    for i, (lab, v, col) in enumerate(items):
        bh = (h - top - bottom) * v / vmax
        x = left + i * bw + bw * 0.18
        y = h - bottom - bh
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw * 0.64:.1f}" height="{bh:.1f}" rx="4" '
                    f'fill="{col or PALETTE[0]}"><title>{escape(lab)}: {v:,.0f}</title></rect>')
        body.append(f'<text x="{x + bw * 0.32:.1f}" y="{h - 14}" text-anchor="middle" font-size="11" fill="#6b7280">{escape(lab)}</text>')
    return _frame(w, h, "".join(body), label)


def line_chart(history, forecast=None, label="Actual vs forecast", w=640, h=250):
    """history = [(YYYY-MM, value)]; forecast = (YYYY-MM, value) drawn as a dashed extension + dot."""
    pts = list(history)
    if not pts:
        return Markup('<p class="muted">No history to chart yet.</p>')
    allv = [v for _, v in pts] + ([forecast[1]] if forecast else [])
    vmax = max(allv) * 1.15 or 1
    n = len(pts) + (1 if forecast else 0)
    left, top, bottom = 46, 14, 34
    step = (w - left - 20) / max(1, n - 1)

    def xy(i, v):
        return left + i * step, top + (h - top - bottom) * (1 - v / vmax)

    body = [_grid(w, h, left, top, bottom, vmax)]
    coords = [xy(i, v) for i, (_, v) in enumerate(pts)]
    body.append('<polyline fill="none" stroke="#315fe8" stroke-width="2.5" points="'
                + " ".join(f"{x:.1f},{y:.1f}" for x, y in coords) + '"/>')
    for (x, y), (m, v) in zip(coords, pts):
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#315fe8"><title>{_mlabel(m)}: {v:,.0f}</title></circle>')
    labels = [(i, m) for i, (m, _) in enumerate(pts)]
    if forecast:
        fx, fy = xy(len(pts), forecast[1])
        lx, ly = coords[-1]
        body.append(f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{fx:.1f}" y2="{fy:.1f}" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="6 5"/>')
        body.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="6" fill="#f59e0b"><title>Forecast {_mlabel(forecast[0])}: {forecast[1]:,.0f}</title></circle>')
        labels.append((len(pts), forecast[0]))
    every = 1 if n <= 8 else 2
    for i, m in labels:
        if i % every == 0 or i == n - 1:
            x, _ = xy(i, 0)
            body.append(f'<text x="{x:.1f}" y="{h - 14}" text-anchor="middle" font-size="11" fill="#6b7280">{_mlabel(m)}</text>')
    return _frame(w, h, "".join(body), label)


def donut(items, label="Spending by category", size=220):
    """items = [(label, value)] -> donut + legend."""
    items = [(l, v) for l, v in items if v > 0]
    if not items:
        return Markup('<p class="muted">No expenses this month yet.</p>')
    import math
    total = sum(v for _, v in items)
    cx = cy = size / 2
    r, rw = size / 2 - 8, 34
    arcs, legend, ang = [], [], -math.pi / 2
    for i, (lab, v) in enumerate(sorted(items, key=lambda t: -t[1])):
        col = PALETTE[i % len(PALETTE)]
        frac = v / total
        legend.append(f'<li><span class="dot" style="background:{col}"></span>{escape(lab)} <b>{frac:.0%}</b></li>')
        if frac >= 0.9999:
            arcs.append(f'<circle cx="{cx}" cy="{cy}" r="{r - rw / 2}" fill="none" stroke="{col}" stroke-width="{rw}"/>')
            continue
        a2 = ang + 2 * math.pi * frac
        x1, y1, x2, y2 = cx + r * math.cos(ang), cy + r * math.sin(ang), cx + r * math.cos(a2), cy + r * math.sin(a2)
        ri = r - rw
        x3, y3, x4, y4 = cx + ri * math.cos(a2), cy + ri * math.sin(a2), cx + ri * math.cos(ang), cy + ri * math.sin(ang)
        big = 1 if frac > 0.5 else 0
        arcs.append(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {big} 1 {x2:.1f},{y2:.1f} L{x3:.1f},{y3:.1f} '
                    f'A{ri},{ri} 0 {big} 0 {x4:.1f},{y4:.1f} Z" fill="{col}"><title>{escape(lab)}: {v:,.0f}</title></path>')
        ang = a2
    svg = (f'<svg viewBox="0 0 {size} {size}" class="donut" role="img" aria-label="{escape(label)}">{"".join(arcs)}'
           f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="12" fill="#6b7280">Total</text>'
           f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-size="18" font-weight="700" fill="#111827">{_short(total)}</text></svg>')
    return Markup(f'<div class="donut-wrap">{svg}<ul class="legend">{"".join(legend)}</ul></div>')
