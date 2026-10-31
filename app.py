import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table, Input, Output, State, ctx, no_update

import db
from layout_engine import optimize

try:
    db.init()
    DB_ERR = None
except Exception as e:  # app stays usable without DB
    DB_ERR = str(e)

CSS = """
:root{--cyan:#22d3ee;--violet:#a78bfa;--pink:#f472b6;--text:#e6f1ff;--muted:#8fa3c4;
--glass-b:rgba(255,255,255,.14)}
*{box-sizing:border-box}
html{background:#050816;min-height:100%}
body{margin:0;background:transparent;color:var(--text);font-family:Inter,system-ui,sans-serif;min-height:100vh}
body::before{content:"";position:fixed;inset:-10%;z-index:-2;pointer-events:none;
background:radial-gradient(45vw 45vw at 10% 10%,rgba(34,211,238,.32),transparent 60%),
radial-gradient(45vw 45vw at 90% 15%,rgba(167,139,250,.34),transparent 60%),
radial-gradient(45vw 45vw at 55% 100%,rgba(244,114,182,.26),transparent 60%);
animation:drift 16s ease-in-out infinite alternate}
body::after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),
linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);background-size:46px 46px;
-webkit-mask-image:radial-gradient(ellipse at center,#000 25%,transparent 80%);
mask-image:radial-gradient(ellipse at center,#000 25%,transparent 80%)}
@keyframes drift{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(-3%,3%,0) scale(1.12)}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(34,211,238,.6)}50%{box-shadow:0 0 0 7px rgba(34,211,238,0)}}

.shell{max-width:1500px;margin:0 auto;padding:22px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 24px;margin-bottom:20px;animation:rise .6s both}
.brand{font-family:Orbitron,Inter,sans-serif;font-weight:700;font-size:26px;letter-spacing:.06em;margin:0;
background:linear-gradient(90deg,var(--cyan),var(--violet) 55%,var(--pink));-webkit-background-clip:text;background-clip:text;
color:transparent;text-shadow:0 0 30px rgba(34,211,238,.25)}
.sub{color:var(--muted);font-size:13px;margin-top:4px;letter-spacing:.04em}
.badge{display:inline-flex;align-items:center;gap:8px;padding:7px 14px;border-radius:999px;font-size:12px;
background:rgba(255,255,255,.07);border:1px solid var(--glass-b);color:var(--text);white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:#34d399;animation:pulse 2s infinite}
.dot.warn{background:#fbbf24}
.main{display:flex;gap:20px;align-items:flex-start}
.glass{background:linear-gradient(135deg,rgba(255,255,255,.11),rgba(255,255,255,.035));border:1px solid var(--glass-b);
border-radius:22px;-webkit-backdrop-filter:blur(20px) saturate(160%);backdrop-filter:blur(20px) saturate(160%);
box-shadow:0 10px 44px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.2)}
.side{width:290px;flex-shrink:0;padding:22px;animation:rise .7s .1s both}
.content{flex:1;min-width:0;padding:10px 18px 22px;animation:rise .7s .2s both}
.h-sec{font-family:Orbitron,Inter,sans-serif;font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);margin:0 0 6px}
.lbl{display:block;margin:14px 0 6px;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.gi{display:flex;align-items:center;gap:6px;width:100%;padding:3px 8px 3px 12px;border-radius:12px;color:var(--text);
background:rgba(5,8,22,.45);border:1px solid rgba(255,255,255,.14);transition:.2s}
.gi:focus-within{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(34,211,238,.18),0 0 18px rgba(34,211,238,.25)}
.gi .dash-input-element,input.gi{flex:1;min-width:0;padding:8px 0;background:transparent!important;border:0!important;outline:none!important;
color:var(--text)!important;font:500 14px Inter,sans-serif;-moz-appearance:textfield}
.gi input::-webkit-outer-spin-button,.gi input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.dash-input-stepper{width:24px;height:24px;border:1px solid rgba(255,255,255,.14);border-radius:8px;cursor:pointer;line-height:1;
background:rgba(255,255,255,.08);color:var(--cyan);font-size:15px;padding:0;transition:.15s}
.dash-input-stepper:hover{background:rgba(34,211,238,.25);box-shadow:0 0 12px rgba(34,211,238,.4)}
.btn{cursor:pointer;border:0;border-radius:14px;padding:12px 18px;font:700 13px Orbitron,Inter,sans-serif;letter-spacing:.12em;
text-transform:uppercase;color:#04101c;background:linear-gradient(90deg,var(--cyan),var(--violet));
box-shadow:0 6px 24px rgba(34,211,238,.35);transition:transform .18s,box-shadow .18s,filter .18s}
.btn:hover{transform:translateY(-2px);box-shadow:0 10px 32px rgba(167,139,250,.55);filter:brightness(1.08)}
.btn:active{transform:translateY(0)}
.btn.full{width:100%;margin-top:22px}
.btn.ghost{color:var(--text);background:rgba(255,255,255,.08);border:1px solid var(--glass-b);box-shadow:none;font-size:12px;padding:9px 14px}
.btn.ghost:hover{background:rgba(255,255,255,.15);box-shadow:0 0 18px rgba(34,211,238,.3)}
.btn.danger:hover{box-shadow:0 0 18px rgba(244,114,182,.5);border-color:var(--pink)}
.err{color:#fda4af;font-size:13px;margin-top:10px;min-height:16px}
.okmsg{color:#6ee7b7;font-size:13px;margin-left:14px}

.tabs-bar{display:flex!important;gap:8px;border:0!important;background:transparent!important;margin:8px 0 16px;flex-wrap:wrap}
.tab{padding:9px 20px!important;border:1px solid var(--glass-b)!important;border-radius:999px!important;cursor:pointer;
background:rgba(255,255,255,.05)!important;color:var(--muted)!important;font:600 13px Inter,sans-serif!important;
letter-spacing:.06em;transition:.2s;width:auto!important}
.tab:hover{color:var(--text)!important;background:rgba(255,255,255,.12)!important}
.tab-sel,.tab-sel:hover{color:#04101c!important;background:linear-gradient(90deg,var(--cyan),var(--violet))!important;
border-color:transparent!important;box-shadow:0 0 22px rgba(34,211,238,.45)}
.tab-body{animation:rise .45s both}
.row{display:flex;gap:24px;flex-wrap:wrap}
.panel{padding:16px;border-radius:18px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1)}
.hint{font-size:12px;color:var(--muted);margin-top:8px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:6px 0 18px}
.stat{padding:16px 18px;border-radius:18px;background:linear-gradient(135deg,rgba(255,255,255,.1),rgba(255,255,255,.03));
border:1px solid var(--glass-b);box-shadow:inset 0 1px 0 rgba(255,255,255,.18);transition:.25s}
.stat:hover{transform:translateY(-3px);box-shadow:0 0 28px rgba(34,211,238,.3)}
.stat .k{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.stat .v{font:700 30px Orbitron,Inter,sans-serif;margin:6px 0 2px;background:linear-gradient(90deg,var(--cyan),var(--violet));
-webkit-background-clip:text;background-clip:text;color:transparent}
.stat .d{font-size:12px;color:#6ee7b7}
.chk label{color:var(--muted);font-size:13px;cursor:pointer}
.chk input{accent-color:var(--cyan)}
.toolbar{display:flex;align-items:center;gap:10px;margin-top:14px;flex-wrap:wrap}

/* dropdown (Dash 4 markup) */
.dash-dropdown.gd{width:100%;display:block;padding:8px 12px;border-radius:12px;cursor:pointer;text-align:left;
background:rgba(5,8,22,.45);border:1px solid rgba(255,255,255,.14);color:var(--text);font:500 14px Inter,sans-serif;transition:.2s}
.dash-dropdown.gd:hover,.dash-dropdown.gd[aria-expanded="true"]{border-color:var(--cyan);box-shadow:0 0 18px rgba(34,211,238,.25)}
.dash-dropdown.gd .dash-dropdown-grid-container{display:flex;align-items:center;justify-content:space-between;gap:8px}
.dash-dropdown.gd .dash-dropdown-value,.dash-dropdown.gd .dash-dropdown-value-item{color:var(--text);background:transparent!important}
.dash-dropdown.gd .dash-dropdown-trigger-icon{color:var(--cyan)}
.dash-dropdown-content{background:rgba(10,14,36,.94)!important;border:1px solid var(--glass-b)!important;border-radius:14px!important;
-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px);box-shadow:0 14px 40px rgba(0,0,0,.6);padding:6px;overflow:hidden;z-index:50}
.dash-dropdown-option{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:10px;color:var(--text)!important;
background:transparent!important;cursor:pointer;font:500 14px Inter,sans-serif}
.dash-dropdown-option:hover,.dash-dropdown-option[data-highlighted]{background:rgba(34,211,238,.16)!important}
.dash-dropdown-option.selected{background:rgba(167,139,250,.22)!important;box-shadow:inset 0 0 0 1px rgba(167,139,250,.5)}
.dash-dropdown-option input{accent-color:var(--cyan)}
.dash-dropdown-content input[type=search],.dash-dropdown-content input[type=text]{background:rgba(5,8,22,.6);color:var(--text);
border:1px solid rgba(255,255,255,.14);border-radius:8px;padding:6px 8px}

/* spinner */
._dash-loading-callback,.dash-spinner{color:var(--cyan)}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,.18);border-radius:8px}
@media(max-width:960px){.main{flex-direction:column}.side{width:100%}.topbar{flex-direction:column;align-items:flex-start}}
"""

app = Dash(__name__, title="Layout Generator")
server = app.server  # gunicorn app:server
app.index_string = (
    "<!DOCTYPE html><html><head>{%metas%}<title>{%title%}</title>{%favicon%}"
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@500;700&display=swap" rel="stylesheet">'
    "{%css%}<style>" + CSS + "</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"
)

DEFAULT_DEPTS = [
    {"name": "Receiving", "area": 120}, {"name": "Storage", "area": 300},
    {"name": "Machining", "area": 250}, {"name": "Assembly", "area": 200},
    {"name": "Paint", "area": 100}, {"name": "Shipping", "area": 120},
]
DEFAULT_FLOWS = {("Receiving", "Storage"): 50, ("Storage", "Machining"): 40,
                 ("Machining", "Assembly"): 35, ("Assembly", "Paint"): 20,
                 ("Paint", "Shipping"): 25, ("Storage", "Assembly"): 15,
                 ("Assembly", "Shipping"): 20}

NEON = ["#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#60a5fa", "#fb7185", "#2dd4bf", "#c084fc", "#facc15"]
TXT = "#e6f1ff"


def rgba(hex_, a):
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def style_fig(fig, height=None):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color=TXT), margin=dict(l=20, r=20, t=50, b=20))
    if height:
        fig.update_layout(height=height)
    return fig


TABLE_KW = dict(
    style_header={"backgroundColor": "rgba(34,211,238,.14)", "color": "#22d3ee", "fontWeight": "700",
                  "border": "1px solid rgba(255,255,255,.12)", "textTransform": "uppercase",
                  "fontSize": "11px", "letterSpacing": ".1em"},
    style_data={"backgroundColor": "rgba(255,255,255,.04)", "color": TXT, "border": "1px solid rgba(255,255,255,.08)"},
    style_data_conditional=[{"if": {"state": "active"}, "backgroundColor": "rgba(34,211,238,.18)",
                             "border": "1px solid #22d3ee"},
                            {"if": {"state": "selected"}, "backgroundColor": "rgba(167,139,250,.2)",
                             "border": "1px solid #a78bfa"}],
    style_cell={"fontFamily": "Inter, sans-serif", "padding": "9px 12px", "backgroundColor": "transparent",
                "color": TXT, "minWidth": "80px", "textAlign": "left"},
    css=[{"selector": ".dash-spreadsheet td input, .dash-spreadsheet td textarea",
          "rule": "color:#e6f1ff!important;background:rgba(5,8,22,.85)!important"},
         {"selector": ".dash-filter input", "rule": "color:#e6f1ff!important"},
         {"selector": ".previous-next-container, .page-number", "rule": "color:#e6f1ff!important"}],
)


def valid_rows(dept):
    out = []
    for r in dept or []:
        nm = str(r.get("name") or "").strip()
        try:
            ar = float(r.get("area"))
        except (TypeError, ValueError):
            continue
        if nm and ar > 0:
            out.append((nm, ar))
    return out


def empty_fig(text):
    f = go.Figure()
    f.add_annotation(text=text, showarrow=False, font=dict(size=16, color="#8fa3c4"))
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    return style_fig(f, 520)


def layout_fig(res, show_flows=True, top_n=8):
    names, R, W, H = res["names"], np.array(res["R"]), res["W"], res["H"]
    F = np.array(res["flow"])
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=W, y1=H, line=dict(width=2, color="#22d3ee", dash="dot"),
                  fillcolor="rgba(255,255,255,.02)")
    for i in range(len(names)):
        x, y, w, h = R[i]
        c = NEON[i % len(NEON)]
        fig.add_shape(type="rect", x0=x, y0=y, x1=x + w, y1=y + h, fillcolor=rgba(c, .28),
                      line=dict(width=2, color=c), layer="below")
    fig.add_trace(go.Scatter(
        x=R[:, 0] + R[:, 2] / 2, y=R[:, 1] + R[:, 3] / 2, mode="text",
        text=[f"<b>{n}</b><br>{R[i,2]:.1f}×{R[i,3]:.1f}" for i, n in enumerate(names)],
        textfont=dict(color="#ffffff", size=13),
        hovertext=[f"{n}: {R[i,2]*R[i,3]:.0f} sq units" for i, n in enumerate(names)],
        hoverinfo="text", showlegend=False))
    if show_flows:
        pairs = sorted(((F[i, j], i, j) for i in range(len(names)) for j in range(len(names))
                        if F[i, j] > 0), reverse=True)[:top_n]
        mx = pairs[0][0] if pairs else 1
        for f, i, j in pairs:
            fig.add_annotation(x=R[j, 0] + R[j, 2] / 2, y=R[j, 1] + R[j, 3] / 2,
                               ax=R[i, 0] + R[i, 2] / 2, ay=R[i, 1] + R[i, 3] / 2,
                               xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                               arrowhead=2, arrowsize=1.1, arrowwidth=1 + 2.5 * f / mx, arrowcolor="rgba(244,114,182,.7)",
                               standoff=22, startstandoff=22)
    fig.update_xaxes(range=[-1, W + 1], showgrid=True, gridcolor="rgba(255,255,255,.06)", zeroline=False, constrain="domain")
    fig.update_yaxes(range=[-1, H + 1], scaleanchor="x", showgrid=True, gridcolor="rgba(255,255,255,.06)", zeroline=False)
    style_fig(fig, 640)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def lbl(t):
    return html.Label(t, className="lbl")


side = html.Div([
    html.H3("Control Deck", className="h-sec"),
    lbl("Run name"), dcc.Input(id="pname", value="Plant layout v1", className="gi"),
    lbl("Plot width"), dcc.Input(id="W", type="number", value=40, min=5, className="gi"),
    lbl("Plot height"), dcc.Input(id="H", type="number", value=30, min=5, className="gi"),
    lbl("Algorithm"),
    dcc.Dropdown(id="algo", options=["CRAFT (swap)", "Simulated annealing"], value="CRAFT (swap)", clearable=False, searchable=False, className="gd"),
    lbl("Bands (rows)"),
    dcc.Dropdown(id="bands", options=[{"label": "auto", "value": 0}] + [{"label": str(i), "value": i} for i in range(1, 5)],
                 value=0, clearable=False, searchable=False, className="gd"),
    lbl("Iterations"), dcc.Input(id="iters", type="number", value=3000, min=100, max=20000, className="gi"),
    lbl("Max aspect ratio"), dcc.Input(id="maxar", type="number", value=4, min=1.5, max=10, step=0.5, className="gi"),
    lbl("Seed"), dcc.Input(id="seed", type="number", value=1, className="gi"),
    html.Button("⚡ Generate", id="run", n_clicks=0, className="btn full"),
    html.Div(id="msg", className="err"),
], className="glass side")

tab_inputs = html.Div([
    html.Div([
        html.Div([
            html.H4("Departments", className="h-sec"),
            dash_table.DataTable(id="dept", data=DEFAULT_DEPTS, editable=True, row_deletable=True,
                                 columns=[{"name": "name", "id": "name"}, {"name": "area", "id": "area", "type": "numeric"}],
                                 **TABLE_KW),
            html.Button("+ Add department", id="add", n_clicks=0, className="btn ghost", style={"marginTop": "12px"}),
        ], className="panel", style={"width": "310px"}),
        html.Div([
            html.H4("Flow matrix  ·  from row → to column", className="h-sec"),
            dash_table.DataTable(id="flow", data=[], columns=[], editable=True,
                                 style_table={"overflowX": "auto"}, **TABLE_KW),
            html.Div("Renaming a dept resets its flow values.", className="hint"),
        ], className="panel", style={"flex": "1", "minWidth": "300px"}),
    ], className="row"),
], className="tab-body")

tab_layout = html.Div([
    dcc.Checklist(id="show-flows", options=[{"label": " Show top flows", "value": "y"}], value=["y"], className="chk"),
    dcc.Loading(dcc.Graph(id="layout-graph", figure=empty_fig("Set inputs, then hit Generate"),
                          config={"displaylogo": False}), color="#22d3ee", type="circle"),
], className="tab-body")

tab_metrics = html.Div([
    html.Div([
        html.Button("💾 Save run", id="save", n_clicks=0, className="btn ghost"),
        html.Span(id="save-msg", className="okmsg"),
    ], className="toolbar"),
    html.Div(id="metrics", style={"marginTop": "14px"}),
], className="tab-body")

tab_saved = html.Div([
    html.Div([
        dash_table.DataTable(id="runs", data=[], page_size=10,
                             columns=[{"name": c, "id": c} for c in ["id", "name", "algorithm", "cost", "created_at"]],
                             **TABLE_KW),
        html.Div([
            html.Div(dcc.Dropdown(id="run-id", options=[], placeholder="Run id", searchable=False, className="gd"), style={"width": "170px"}),
            html.Button("Load", id="load", n_clicks=0, className="btn ghost"),
            html.Button("Delete", id="delete", n_clicks=0, className="btn ghost danger"),
        ], className="toolbar"),
    ], className="panel"),
], className="tab-body")


def mk_tab(label, value, child):
    return dcc.Tab(label=label, value=value, children=child, className="tab", selected_className="tab-sel",
                   style={}, selected_style={})


app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1("LAYOUT·GEN", className="brand"),
            html.Div("Automated facility layout optimizer", className="sub"),
        ]),
        html.Div([html.Span(className="dot warn" if DB_ERR else "dot"),
                  f"DB: {db.BACKEND}" + (" ⚠ error" if DB_ERR else "")], className="badge", title=DB_ERR or ""),
    ], className="glass topbar"),
    html.Div([
        side,
        html.Div([
            dcc.Tabs(id="tabs", value="inputs", className="tabs-bar", parent_className="tabs-parent", children=[
                mk_tab("Inputs", "inputs", tab_inputs),
                mk_tab("Layout", "layout", tab_layout),
                mk_tab("Metrics", "metrics", tab_metrics),
                mk_tab("Saved runs", "saved", tab_saved),
            ]),
        ], className="glass content"),
    ], className="main"),
    dcc.Store(id="result"),
], className="shell")


@app.callback(Output("dept", "data"), Input("add", "n_clicks"), State("dept", "data"), prevent_initial_call=True)
def add_dept(_, rows):
    return (rows or []) + [{"name": f"Dept {len(rows or []) + 1}", "area": 100}]


@app.callback(Output("flow", "columns"), Output("flow", "data"), Input("dept", "data"), State("flow", "data"))
def sync_flow(dept, old):
    names = [n for n, _ in valid_rows(dept)]
    old_map = {r.get("from"): r for r in (old or [])}
    rows = []
    for a in names:
        r = {"from": a}
        for b in names:
            r[b] = old_map.get(a, {}).get(b, 0) if old else DEFAULT_FLOWS.get((a, b), 0)
        rows.append(r)
    cols = [{"name": "from \\ to", "id": "from", "editable": False}] + \
           [{"name": n, "id": n, "type": "numeric"} for n in names]
    return cols, rows


@app.callback(
    Output("result", "data"), Output("msg", "children"),
    Input("run", "n_clicks"),
    State("dept", "data"), State("flow", "data"), State("pname", "value"), State("W", "value"),
    State("H", "value"), State("algo", "value"), State("bands", "value"), State("iters", "value"),
    State("maxar", "value"), State("seed", "value"), prevent_initial_call=True)
def generate(_, dept, flow, pname, W, H, algo, bands, iters, maxar, seed):
    rows = valid_rows(dept)
    names = [n for n, _ in rows]
    areas = [a for _, a in rows]
    if not W or not H:
        return None, "Enter plot width and height."
    if len(names) < 2 or len(set(names)) != len(names):
        return None, "Need ≥2 departments with unique names."
    if sum(areas) > W * H:
        return None, f"Total dept area {sum(areas):.0f} > plot area {W*H:.0f}."
    fm = {r.get("from"): r for r in (flow or [])}
    F = np.zeros((len(names), len(names)))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            try:
                F[i, j] = float(fm.get(a, {}).get(b) or 0)
            except (TypeError, ValueError):
                F[i, j] = 0.0
    out = optimize(areas, F, float(W), float(H), int(bands or 0), algo, int(iters or 3000),
                   float(maxar or 4), int(seed or 0))
    res = dict(name=pname or "run", algo=algo, names=names, W=float(W), H=float(H),
               R=out["R"].tolist(), flow=F.tolist(), areas=areas, cost=out["cost"],
               flow_cost=out["flow_cost"], base_cost=out["base_cost"], history=out["history"],
               bands=out["bands"], max_ar=float(maxar or 4))
    return res, ""


def stat(k, v, d=None):
    return html.Div([html.Div(k, className="k"), html.Div(v, className="v")] + ([html.Div(d, className="d")] if d else []),
                    className="stat")


@app.callback(Output("layout-graph", "figure"), Output("metrics", "children"),
              Input("result", "data"), Input("show-flows", "value"))
def render(res, show):
    if not res:
        return empty_fig("Set inputs, then hit Generate"), html.P("No run yet.", className="hint")
    R = np.array(res["R"])
    imp = 100 * (res["base_cost"] - res["cost"]) / res["base_cost"] if res["base_cost"] else 0
    cards = html.Div([
        stat("Total cost", f"{res['cost']:.0f}", f"▼ {imp:.1f}% vs initial"),
        stat("Flow × distance", f"{res['flow_cost']:.0f}"),
        stat("Bands used", str(res["bands"])),
        stat("Area stretch", f"{res['W']*res['H']/sum(res['areas']):.2f}×"),
    ], className="stats")
    tbl = pd.DataFrame({"dept": res["names"], "req_area": res["areas"],
                        "width": R[:, 2].round(2), "height": R[:, 3].round(2)})
    tbl["actual_area"] = (tbl.width * tbl.height).round(1)
    tbl["aspect"] = np.maximum(tbl.width / tbl.height, tbl.height / tbl.width).round(2)
    tbl["ok"] = np.where(tbl.aspect <= res["max_ar"], "✔", "✖")
    hm = pd.DataFrame(res["flow"], index=res["names"], columns=res["names"])
    conv = go.Figure(go.Scatter(y=res["history"], mode="lines", line=dict(color="#22d3ee", width=3),
                                fill="tozeroy", fillcolor="rgba(34,211,238,.12)"))
    conv.update_layout(title="Convergence", xaxis_title="step", yaxis_title="cost")
    heat = go.Figure(go.Heatmap(z=hm.values, x=hm.columns, y=hm.index,
                                colorscale=[[0, "#0b1224"], [.5, "#7c3aed"], [1, "#22d3ee"]]))
    heat.update_layout(title="Flow heatmap")
    for f in (conv, heat):
        style_fig(f, 340)
        f.update_xaxes(gridcolor="rgba(255,255,255,.06)")
        f.update_yaxes(gridcolor="rgba(255,255,255,.06)")
    body = html.Div([
        cards,
        html.Div(dash_table.DataTable(data=tbl.to_dict("records"), columns=[{"name": c, "id": c} for c in tbl.columns], **TABLE_KW),
                 className="panel"),
        html.Div([html.Div(dcc.Graph(figure=conv, config={"displaylogo": False}), className="panel", style={"flex": "1", "minWidth": "300px"}),
                  html.Div(dcc.Graph(figure=heat, config={"displaylogo": False}), className="panel", style={"flex": "1", "minWidth": "300px"})],
                 className="row", style={"marginTop": "16px", "gap": "16px"}),
    ])
    return layout_fig(res, bool(show)), body


@app.callback(
    Output("runs", "data"), Output("run-id", "options"), Output("save-msg", "children"),
    Input("tabs", "value"), Input("save", "n_clicks"), Input("delete", "n_clicks"),
    State("result", "data"), State("run-id", "value"), prevent_initial_call=True)
def db_ops(_t, _s, _d, res, run_id):
    msg = ""
    try:
        if ctx.triggered_id == "save":
            if not res:
                msg = "No run to save."
            else:
                rid = db.save_run(res["name"], res["algo"], res["cost"],
                                  json.dumps({"W": res["W"], "H": res["H"], "names": res["names"],
                                              "areas": res["areas"], "flow": res["flow"]}),
                                  json.dumps(res))
                msg = f"Saved run #{rid}"
        elif ctx.triggered_id == "delete" and run_id:
            db.delete_run(run_id)
        runs = db.list_runs()
    except Exception as e:
        return [], [], f"DB error: {e}"
    return runs, [r["id"] for r in runs], msg


@app.callback(Output("result", "data", allow_duplicate=True), Output("tabs", "value"),
              Input("load", "n_clicks"), State("run-id", "value"), prevent_initial_call=True)
def load_run(_, run_id):
    if not run_id:
        return no_update, no_update
    row = db.get_run(run_id)
    return (json.loads(row["result_json"]), "layout") if row else (no_update, no_update)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
