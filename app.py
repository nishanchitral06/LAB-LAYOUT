import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table, Input, Output, State, ctx

import db
from layout_engine import optimize

try:
    db.init()
    DB_ERR = None
except Exception as e:  # app stays usable without DB
    DB_ERR = str(e)

app = Dash(__name__, title="Layout Generator")
server = app.server  # gunicorn app:server

DEFAULT_DEPTS = [
    {"name": "Receiving", "area": 120}, {"name": "Storage", "area": 300},
    {"name": "Machining", "area": 250}, {"name": "Assembly", "area": 200},
    {"name": "Paint", "area": 100}, {"name": "Shipping", "area": 120},
]
DEFAULT_FLOWS = {("Receiving", "Storage"): 50, ("Storage", "Machining"): 40,
                 ("Machining", "Assembly"): 35, ("Assembly", "Paint"): 20,
                 ("Paint", "Shipping"): 25, ("Storage", "Assembly"): 15,
                 ("Assembly", "Shipping"): 20}

CARD = {"padding": "12px 16px", "border": "1px solid #ddd", "borderRadius": "8px", "minWidth": "140px"}
LBL = {"fontWeight": "600", "marginTop": "10px", "display": "block"}
FULL = {"width": "100%"}


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
    f.add_annotation(text=text, showarrow=False, font=dict(size=16))
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    f.update_layout(height=500)
    return f


def layout_fig(res, show_flows=True, top_n=8):
    names, R, W, H = res["names"], np.array(res["R"]), res["W"], res["H"]
    F = np.array(res["flow"])
    colors = px.colors.qualitative.Set3
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=W, y1=H, line=dict(width=3))
    for i in range(len(names)):
        x, y, w, h = R[i]
        fig.add_shape(type="rect", x0=x, y0=y, x1=x + w, y1=y + h,
                      fillcolor=colors[i % len(colors)], line=dict(width=1.5), opacity=0.9)
    fig.add_trace(go.Scatter(
        x=R[:, 0] + R[:, 2] / 2, y=R[:, 1] + R[:, 3] / 2, mode="text",
        text=[f"<b>{n}</b><br>{R[i,2]:.1f}×{R[i,3]:.1f}" for i, n in enumerate(names)],
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
                               arrowhead=3, arrowwidth=1 + 4 * f / mx, arrowcolor="rgba(200,30,30,0.7)")
    fig.update_xaxes(range=[-1, W + 1], showgrid=False, constrain="domain")
    fig.update_yaxes(range=[-1, H + 1], scaleanchor="x", showgrid=False)
    fig.update_layout(height=620, margin=dict(l=10, r=10, t=10, b=10))
    return fig


sidebar = html.Div([
    html.H3("Inputs"),
    html.Label("Run name", style=LBL), dcc.Input(id="pname", value="Plant layout v1", style=FULL),
    html.Label("Plot width", style=LBL), dcc.Input(id="W", type="number", value=40, min=5, style=FULL),
    html.Label("Plot height", style=LBL), dcc.Input(id="H", type="number", value=30, min=5, style=FULL),
    html.Label("Algorithm", style=LBL),
    dcc.Dropdown(id="algo", options=["CRAFT (swap)", "Simulated annealing"], value="CRAFT (swap)", clearable=False),
    html.Label("Bands (rows)", style=LBL),
    dcc.Dropdown(id="bands", options=[{"label": "auto", "value": 0}] + [{"label": str(i), "value": i} for i in range(1, 5)],
                 value=0, clearable=False),
    html.Label("Iterations", style=LBL), dcc.Input(id="iters", type="number", value=3000, min=100, max=20000, style=FULL),
    html.Label("Max aspect ratio", style=LBL), dcc.Input(id="maxar", type="number", value=4, min=1.5, max=10, step=0.5, style=FULL),
    html.Label("Seed", style=LBL), dcc.Input(id="seed", type="number", value=1, style=FULL),
    html.Button("Generate layout", id="run", n_clicks=0,
                style={"width": "100%", "marginTop": "16px", "padding": "10px", "fontWeight": "700"}),
    html.Div(id="msg", style={"color": "#c00", "marginTop": "8px"}),
    html.Div(f"DB: {db.BACKEND}" + (f" ⚠ {DB_ERR}" if DB_ERR else ""),
             style={"marginTop": "14px", "fontSize": "12px", "color": "#666"}),
], style={"width": "260px", "padding": "16px", "borderRight": "1px solid #ddd", "flexShrink": "0"})

tab_inputs = html.Div([
    html.Div([
        html.H4("Departments"),
        dash_table.DataTable(id="dept", data=DEFAULT_DEPTS, editable=True, row_deletable=True,
                             columns=[{"name": "name", "id": "name"},
                                      {"name": "area", "id": "area", "type": "numeric"}]),
        html.Button("+ Add department", id="add", n_clicks=0, style={"marginTop": "8px"}),
    ], style={"width": "300px", "marginRight": "24px"}),
    html.Div([
        html.H4("Flow matrix (from row → to column)"),
        dash_table.DataTable(id="flow", data=[], columns=[], editable=True,
                             style_table={"overflowX": "auto"},
                             style_cell={"minWidth": "80px", "textAlign": "center"}),
        html.Div("Renaming a dept resets its flow values.", style={"fontSize": "12px", "color": "#666", "marginTop": "6px"}),
    ], style={"flex": "1", "minWidth": "0"}),
], style={"display": "flex", "padding": "12px"})

tab_layout = html.Div([
    dcc.Checklist(id="show-flows", options=[{"label": " Show top flows", "value": "y"}], value=["y"]),
    dcc.Graph(id="layout-graph", figure=empty_fig("Set inputs, then click Generate layout")),
], style={"padding": "12px"})

tab_metrics = html.Div([
    html.Button("Save run to DB", id="save", n_clicks=0),
    html.Span(id="save-msg", style={"marginLeft": "12px"}),
    html.Div(id="metrics"),
], style={"padding": "12px"})

tab_saved = html.Div([
    dash_table.DataTable(id="runs", data=[], page_size=10,
                         columns=[{"name": c, "id": c} for c in ["id", "name", "algorithm", "cost", "created_at"]]),
    html.Div([
        dcc.Dropdown(id="run-id", options=[], placeholder="Run id", style={"width": "160px"}),
        html.Button("Load", id="load", n_clicks=0, style={"marginLeft": "8px"}),
        html.Button("Delete", id="delete", n_clicks=0, style={"marginLeft": "8px"}),
    ], style={"display": "flex", "alignItems": "center", "marginTop": "12px"}),
], style={"padding": "12px"})

app.layout = html.Div([
    sidebar,
    html.Div([
        html.H2("Automated Layout Generator", style={"padding": "0 12px"}),
        dcc.Tabs(id="tabs", value="inputs", children=[
            dcc.Tab(label="Inputs", value="inputs", children=tab_inputs),
            dcc.Tab(label="Layout", value="layout", children=tab_layout),
            dcc.Tab(label="Metrics", value="metrics", children=tab_metrics),
            dcc.Tab(label="Saved runs", value="saved", children=tab_saved),
        ]),
    ], style={"flex": "1", "minWidth": "0"}),
    dcc.Store(id="result"),
], style={"display": "flex", "fontFamily": "system-ui, sans-serif"})


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


@app.callback(Output("layout-graph", "figure"), Output("metrics", "children"),
              Input("result", "data"), Input("show-flows", "value"))
def render(res, show):
    if not res:
        return empty_fig("Set inputs, then click Generate layout"), html.P("No run yet.")
    R = np.array(res["R"])
    imp = 100 * (res["base_cost"] - res["cost"]) / res["base_cost"] if res["base_cost"] else 0
    cards = html.Div([
        html.Div([html.Div("Total cost"), html.H3(f"{res['cost']:.0f}"), html.Small(f"-{imp:.1f}% vs initial")], style=CARD),
        html.Div([html.Div("Flow × distance"), html.H3(f"{res['flow_cost']:.0f}")], style=CARD),
        html.Div([html.Div("Bands used"), html.H3(str(res["bands"]))], style=CARD),
        html.Div([html.Div("Area stretch"), html.H3(f"{res['W']*res['H']/sum(res['areas']):.2f}×")], style=CARD),
    ], style={"display": "flex", "gap": "12px", "margin": "12px 0"})
    tbl = pd.DataFrame({"dept": res["names"], "req_area": res["areas"],
                        "width": R[:, 2].round(2), "height": R[:, 3].round(2)})
    tbl["actual_area"] = (tbl.width * tbl.height).round(1)
    tbl["aspect"] = np.maximum(tbl.width / tbl.height, tbl.height / tbl.width).round(2)
    tbl["ok"] = tbl.aspect <= res["max_ar"]
    hm = pd.DataFrame(res["flow"], index=res["names"], columns=res["names"])
    body = html.Div([
        cards,
        dash_table.DataTable(data=tbl.astype({"ok": str}).to_dict("records"),
                             columns=[{"name": c, "id": c} for c in tbl.columns]),
        dcc.Graph(figure=px.line(y=res["history"], labels={"x": "step", "y": "cost"}, title="Convergence")),
        dcc.Graph(figure=px.imshow(hm, title="Flow heatmap", color_continuous_scale="Reds")),
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


from dash import no_update  # noqa: E402

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
