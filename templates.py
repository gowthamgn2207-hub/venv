"""HTML templates (Jinja) for FinTrack. Kept in one place so the app is easy to read and deploy."""

BASE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}FinTrack{% endblock %} · FinTrack</title>
<style>
:root{--blue:#315fe8;--bg:#f3f5fa;--card:#fff;--ink:#111827;--muted:#6b7280;--line:#e5e8f0;--green:#16a37f;--red:#ef4444;--amber:#f59e0b}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.45}
a{color:var(--blue);text-decoration:none}.muted{color:var(--muted)}small{color:var(--muted)}
.side{position:fixed;left:0;top:0;bottom:0;width:224px;background:#fff;border-right:1px solid var(--line);padding:20px 14px;display:flex;flex-direction:column;gap:4px}
.brand{font-weight:800;font-size:20px;color:var(--blue);padding:0 10px 16px}
.side a.nav{padding:10px 12px;border-radius:10px;color:#374151;font-weight:600}.side a.nav.on,.side a.nav:hover{background:#eaf0ff;color:var(--blue)}
.side .who{margin-top:auto;padding:10px;font-size:13px;color:var(--muted)}
main{margin-left:224px;padding:28px 32px;max-width:1100px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}
.card{background:var(--card);border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:18px}
.grid{display:grid;gap:16px}.g4{grid-template-columns:repeat(4,1fr)}.g2{grid-template-columns:1fr 1fr}
.stat .lab{font-size:13px;color:var(--muted)}.stat .val{font-size:24px;font-weight:800;margin-top:4px}
.pos{color:var(--green)}.neg{color:var(--red)}
.btn{display:inline-block;background:var(--blue);color:#fff;border:0;border-radius:10px;padding:10px 16px;font-weight:700;font-size:14px;cursor:pointer}
.btn.sec{background:#eaf0ff;color:var(--blue)}.btn.danger{background:#fee2e2;color:#b91c1c}.btn.sm{padding:6px 10px;font-size:13px}
label{display:block;font-size:13px;font-weight:600;margin:12px 0 4px}
input,select{width:100%;padding:10px 12px;border:1px solid #d5d9e4;border-radius:10px;font-size:15px;background:#fff}
input:focus,select:focus{outline:2px solid #c7d6ff;border-color:var(--blue)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 8px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase}
td.r,th.r{text-align:right}.tablewrap{overflow-x:auto}
.flash{padding:12px 14px;border-radius:10px;margin-bottom:14px;font-size:14px}.flash.error{background:#fee2e2;color:#991b1b}.flash.ok{background:#dcfce7;color:#166534}
.badge{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:700;background:#eaf0ff;color:var(--blue)}.badge.warn{background:#fef3c7;color:#92400e}
.chart{width:100%;height:auto}.donut-wrap{display:flex;gap:20px;align-items:center;flex-wrap:wrap}.donut{width:200px;height:200px}
.legend{list-style:none;margin:0;padding:0;font-size:14px}.legend li{margin:5px 0}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
.bar{background:#e8ecf5;border-radius:99px;height:10px;overflow:hidden}.bar>i{display:block;height:100%;background:var(--blue)}.bar.warn>i{background:var(--amber)}.bar.over>i{background:var(--red)}
.rec{padding:12px 14px;border-radius:10px;margin-bottom:10px;font-size:14px;border-left:4px solid}
.rec.danger{background:#fef2f2;border-color:var(--red)}.rec.warn{background:#fffbeb;border-color:var(--amber)}.rec.tip{background:#eff6ff;border-color:var(--blue)}.rec.info{background:#f8fafc;border-color:#94a3b8}.rec.good{background:#f0fdf4;border-color:var(--green)}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.row>*{flex:1;min-width:140px}.row .auto{flex:0}
.auth{max-width:420px;margin:7vh auto;padding:0 16px}.auth .card{padding:28px}
.note{font-size:13px;color:var(--muted);background:#f8fafc;border-radius:10px;padding:10px 12px;margin-top:12px}
.demo-box{background:#eff6ff;border:1px dashed var(--blue);border-radius:12px;padding:12px 14px;font-size:14px;margin-top:14px}
code{background:#eef1f8;padding:2px 6px;border-radius:6px;font-size:13px}
.tabs{display:none}
@media(max-width:820px){.side{display:none}main{margin:0;padding:18px 16px 90px}.g4{grid-template-columns:1fr 1fr}.g2{grid-template-columns:1fr}
.tabs{display:flex;position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--line);justify-content:space-around;padding:8px 4px;z-index:5}
.tabs a{font-size:11px;font-weight:600;color:#6b7280;text-align:center;padding:4px 6px}.tabs a.on{color:var(--blue)}}
</style></head><body>
{% if user %}
<nav class="side"><div class="brand">FinTrack</div>
{% for ep,name in NAV %}<a class="nav {{ 'on' if request.endpoint==ep }}" href="{{ url_for(ep) }}">{{ name }}</a>{% endfor %}
<div class="who">{{ user.name }}<br><small>{{ user.email }}</small>
<form method="post" action="{{ url_for('logout') }}" style="margin-top:8px"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn sec sm">Log out</button></form></div></nav>
<nav class="tabs">{% for ep,name in NAV %}<a class="{{ 'on' if request.endpoint==ep }}" href="{{ url_for(ep) }}">{{ name }}</a>{% endfor %}</nav>
{% endif %}
<main>{% with msgs = get_flashed_messages(with_categories=true) %}{% for c,m in msgs %}<div class="flash {{ c }}">{{ m }}</div>{% endfor %}{% endwith %}
{% block body %}{% endblock %}</main></body></html>"""

AUTH = r"""{% extends "base.html" %}{% block title %}{{ heading }}{% endblock %}
{% block body %}<div class="auth"><div style="text-align:center;margin-bottom:14px"><div class="brand" style="padding:0">FinTrack</div><small>AI-Based Personal Finance Management and Expense Forecasting</small></div>
<div class="card"><h2>{{ heading }}</h2>
<form method="post" autocomplete="on"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
{% if register %}<label>Name</label><input name="name" required maxlength="60" value="{{ form.get('name','') }}">{% endif %}
<label>Email</label><input type="email" name="email" required maxlength="120" value="{{ form.get('email','') }}">
<label>Password{% if register %} (min 8 characters){% endif %}</label><input type="password" name="password" required minlength="{{ 8 if register else 1 }}" maxlength="128">
<button class="btn" style="width:100%;margin-top:18px">{{ heading }}</button></form>
<p style="margin-top:16px;text-align:center">{% if register %}Already registered? <a href="{{ url_for('login') }}">Log in</a>{% else %}New here? <a href="{{ url_for('register') }}">Create an account</a>{% endif %}</p>
{% if not register and demo_email %}<div class="demo-box"><b>Try the demo account</b><br>Email: <code>{{ demo_email }}</code><br>Password: <code>{{ demo_password }}</code><br><small>It comes with 24 months of sample data so the ML models have something to learn from.</small></div>{% endif %}
</div></div>{% endblock %}"""

DASH = r"""{% extends "base.html" %}{% block title %}Dashboard{% endblock %}
{% block body %}<h1>Hello, {{ user.name.split()[0] }}</h1><p class="muted">{{ month_name }} overview</p>
<div class="grid g4">
<div class="card stat"><div class="lab">Monthly income</div><div class="val pos">₹{{ income|inr }}</div></div>
<div class="card stat"><div class="lab">Monthly expenses</div><div class="val neg">₹{{ expenses|inr }}</div></div>
<div class="card stat"><div class="lab">Remaining cash flow</div><div class="val {{ 'pos' if remaining>=0 else 'neg' }}">₹{{ remaining|inr }}</div></div>
<div class="card stat"><div class="lab">ML forecast, full {{ month_name.split()[0] }}</div><div class="val">{% if fc.total %}₹{{ fc.total|inr }}{% else %}–{% endif %}</div><small>{{ fc.method_label }}</small></div></div>
<div class="grid g2"><div class="card"><h2>Expenses by category</h2>{{ donut }}</div>
<div class="card"><h2>Last 6 months</h2>{{ bars }}</div></div>
{% if not has_data %}<div class="card"><h2>Nothing here yet</h2><p>Add your first transaction, or load sample data to see the Random Forest, K-Means and Naive Bayes models working.</p>
<a class="btn" href="{{ url_for('add_transaction') }}">Add transaction</a>
<form method="post" action="{{ url_for('demo_load') }}" style="display:inline"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn sec">Load sample data</button></form></div>
{% else %}<div class="card"><h2>Quick actions</h2><a class="btn" href="{{ url_for('add_transaction') }}">Add transaction</a> <a class="btn sec" href="{{ url_for('forecast_page') }}">See forecast</a> <a class="btn sec" href="{{ url_for('insights') }}">AI insights</a>
<form method="post" action="{{ url_for('demo_clear') }}" style="display:inline" onsubmit="return confirm('Remove the sample data? Your own entries are kept.')"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn danger">Remove sample data</button></form></div>{% endif %}{% endblock %}"""

ADD = r"""{% extends "base.html" %}{% block title %}Add transaction{% endblock %}
{% block body %}<h1>Add transaction</h1><p class="muted">Choose “Auto-detect” and the Naive Bayes model picks the category from the description.</p>
<div class="card" style="max-width:640px"><form method="post" id="f"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<div class="row"><div><label>Type</label><select name="kind" id="kind"><option value="expense">Expense</option><option value="income">Income</option></select></div>
<div><label>Amount (₹)</label><input name="amount" type="number" step="0.01" min="0.01" max="999999999" required></div></div>
<label>Description</label><input name="description" id="desc" maxlength="120" placeholder="e.g. Swiggy dinner" autocomplete="off">
<div class="row"><div><label>Category</label><select name="category" id="cat"><option value="auto">Auto-detect (ML)</option></select></div>
<div><label>Payment method</label><select name="payment">{% for p in payments %}<option>{{ p }}</option>{% endfor %}</select></div></div>
<div id="preview" class="note" style="display:none"></div>
<label>Date</label><input type="date" name="date" value="{{ today }}" max="{{ today }}" required>
<button class="btn" style="margin-top:18px">Save transaction</button></form></div>
<script>
const EXP={{ exp_cats|tojson }},INC={{ inc_cats|tojson }},T="{{ csrf_token() }}";
const kind=document.getElementById('kind'),cat=document.getElementById('cat'),desc=document.getElementById('desc'),pv=document.getElementById('preview');
function fill(){const l=kind.value==='income'?INC:EXP;cat.innerHTML='<option value="auto">Auto-detect (ML)</option>'+l.map(c=>'<option>'+c+'</option>').join('');detect()}
let timer;function detect(){clearTimeout(timer);timer=setTimeout(async()=>{
 if(cat.value!=='auto'||!desc.value.trim()){pv.style.display='none';return}
 try{const r=await fetch('{{ url_for("api_categorize") }}',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':T},body:JSON.stringify({description:desc.value,kind:kind.value})});
 const j=await r.json();pv.style.display='block';pv.textContent='Detected category: '+j.category+'  ('+j.explanation+')'}catch(e){pv.style.display='none'}},250)}
kind.onchange=fill;cat.onchange=detect;desc.oninput=detect;fill();
</script>{% endblock %}"""

TX = r"""{% extends "base.html" %}{% block title %}Transactions{% endblock %}
{% block body %}<h1>Transactions</h1>
<div class="card"><form method="get" class="row"><div><label>Search</label><input name="q" value="{{ q }}" placeholder="description"></div>
<div><label>Category</label><select name="category"><option value="">All</option>{% for c in cats %}<option {{ 'selected' if c==category }}>{{ c }}</option>{% endfor %}</select></div>
<div><label>Month</label><input type="month" name="month" value="{{ month }}"></div>
<div class="auto"><button class="btn">Filter</button></div></form></div>
<div class="card tablewrap">{% if rows %}<table><tr><th>Date</th><th>Description</th><th>Category</th><th>Payment</th><th class="r">Amount</th><th></th></tr>
{% for t in rows %}<tr><td>{{ t.date }}</td><td>{{ t.description }}</td><td>{{ t.category }}</td><td>{{ t.payment }}</td>
<td class="r {{ 'pos' if t.kind=='income' else 'neg' }}">{{ '+' if t.kind=='income' else '−' }}₹{{ t.amount|inr }}</td>
<td class="r"><form method="post" action="{{ url_for('delete_transaction', tid=t.id) }}" onsubmit="return confirm('Delete this transaction?')"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn danger sm">Delete</button></form></td></tr>{% endfor %}</table>
{% if capped %}<p class="muted">Showing the latest 300 matches. Use the filters to narrow down.</p>{% endif %}
{% else %}<p class="muted">No transactions match. <a href="{{ url_for('add_transaction') }}">Add one</a>.</p>{% endif %}</div>{% endblock %}"""

BUD = r"""{% extends "base.html" %}{% block title %}Budgets{% endblock %}
{% block body %}<h1>Budgets</h1><p class="muted">{{ month_name }}. Saving a category again updates its limit.</p>
<div class="card" style="max-width:640px"><form method="post" class="row"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<div><label>Category</label><select name="category">{% for c in exp_cats %}<option>{{ c }}</option>{% endfor %}</select></div>
<div><label>Monthly limit (₹)</label><input name="amount" type="number" step="1" min="1" max="999999999" required></div>
<div class="auto"><button class="btn">Save</button></div></form></div>
<div class="card">{% if items %}{% for b in items %}<div style="margin-bottom:18px"><div style="display:flex;justify-content:space-between"><b>{{ b.category }}</b>
<span>₹{{ b.spent|inr }} of ₹{{ b.amount|inr }}</span></div>
<div class="bar {{ 'over' if b.pct>100 else ('warn' if b.pct>80 else '') }}"><i style="width:{{ [b.pct,100]|min }}%"></i></div>
<small>{% if b.left>=0 %}₹{{ b.left|inr }} left{% else %}₹{{ (-b.left)|inr }} over budget{% endif %} · {{ b.pct|round|int }}% used</small>
<form method="post" action="{{ url_for('delete_budget', bid=b.id) }}" style="display:inline;float:right"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn danger sm">Remove</button></form></div>{% endfor %}
{% else %}<p class="muted">No budgets for this month yet. Set one above.</p>{% endif %}</div>{% endblock %}"""

FC = r"""{% extends "base.html" %}{% block title %}Forecast{% endblock %}
{% block body %}<h1>Expense forecast</h1>
<p><span class="badge {{ 'warn' if fc.method!='random_forest' }}">{{ fc.method_label }}</span> <small>for {{ fc.target }} · based on {{ fc.n_months }} complete month(s)</small></p>
{% if fc.method=='none' %}<div class="card"><p>{{ fc.note }}</p>
<form method="post" action="{{ url_for('demo_load') }}"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn">Load sample data</button></form></div>
{% else %}
<div class="grid g2"><div class="card stat"><div class="lab">Predicted total expense</div><div class="val">₹{{ fc.total|inr }}</div></div>
<div class="card stat"><div class="lab">Last complete month</div><div class="val">₹{{ last_total|inr }}</div></div></div>
<div class="card"><h2>Actual vs forecast</h2>{{ chart }}<small>Blue: actual monthly spend. Orange: forecast.</small></div>
<div class="card tablewrap"><h2>By category</h2><table><tr><th>Category</th><th class="r">Last month</th><th class="r">Forecast</th><th class="r">Change</th></tr>
{% for r in fc.per_category %}<tr><td>{{ r.category }}</td><td class="r">₹{{ r.last_month|inr }}</td><td class="r"><b>₹{{ r.predicted|inr }}</b></td>
<td class="r {{ 'neg' if r.predicted>r.last_month else 'pos' }}">{{ '%+.0f'|format((r.predicted-r.last_month)/r.last_month*100) if r.last_month else '–' }}{{ '%' if r.last_month }}</td></tr>{% endfor %}</table></div>
{% if fc.metrics %}<div class="card"><h2>How accurate is it?</h2>
<p>The model was trained on your older months, then tested on your <b>last {{ fc.metrics.holdout_months }} months</b> that it had never seen:</p>
<table><tr><td>Random Forest error (MAE per category)</td><td class="r"><b>₹{{ fc.metrics.mae|inr }}</b></td></tr>
<tr><td>Simple “same as last month” error</td><td class="r">₹{{ fc.metrics.naive_mae|inr }}</td></tr>
<tr><td>R² on unseen months</td><td class="r">{{ '%.2f'|format(fc.metrics.r2) }}</td></tr></table>
<p class="muted">{{ 'The forest beats the naive guess.' if fc.metrics.mae < fc.metrics.naive_mae else 'The forest does not beat the naive guess on your data, so treat this forecast with extra care.' }}</p></div>{% endif %}
{% if fc.importances %}<div class="card"><h2>What the model looks at</h2>{% for n,v in fc.importances %}<div style="margin:8px 0"><div style="display:flex;justify-content:space-between"><span>{{ n }}</span><small>{{ '%.0f'|format(v*100) }}%</small></div><div class="bar"><i style="width:{{ v*100 }}%"></i></div></div>{% endfor %}</div>{% endif %}
<div class="note">{{ fc.note }} This is an estimate, not a guarantee.</div>{% endif %}{% endblock %}"""

INS = r"""{% extends "base.html" %}{% block title %}AI insights{% endblock %}
{% block body %}<h1>AI insights</h1><p class="muted">Alerts come from rules on top of the forecast and clustering models.</p>
<div class="card"><h2>Recommendations</h2>{% for lvl,text in recs %}<div class="rec {{ lvl }}">{{ text }}</div>{% endfor %}</div>
<div class="card"><h2>Spending behaviour (K-Means)</h2>
{% if beh.available %}{{ chart }}<small>Each bar is a complete month, coloured by the cluster K-Means put it in ({{ beh.k }} clusters).</small>
<table style="margin-top:14px"><tr><th>Cluster</th><th class="r">Months</th><th class="r">Avg monthly spend</th><th>Biggest category</th></tr>
{% for s in beh.summary %}<tr><td><span class="dot" style="background:{{ colors[s.label] }}"></span>{{ s.label }}</td><td class="r">{{ s.months }}</td><td class="r">₹{{ s.avg_total|inr }}</td><td>{{ s.top_category }}</td></tr>{% endfor %}</table>
{% else %}<p class="muted">{{ beh.reason }}</p>{% endif %}</div>
<div class="note">Rule-based observations and model output, not professional financial advice.</div>{% endblock %}"""
