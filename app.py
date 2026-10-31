import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import db
from layout_engine import optimize

st.set_page_config(page_title="Layout Generator", layout="wide")


@st.cache_resource
def _init_db():
    try:
        db.init()
        return True
    except Exception as e:  # keep app usable without DB
        return str(e)


DB_OK = _init_db()

DEFAULT_DEPTS = pd.DataFrame({
    "name": ["Receiving", "Storage", "Machining", "Assembly", "Paint", "Shipping"],
    "area": [120, 300, 250, 200, 100, 120],
})
DEFAULT_FLOWS = {("Receiving", "Storage"): 50, ("Storage", "Machining"): 40,
                 ("Machining", "Assembly"): 35, ("Assembly", "Paint"): 20,
                 ("Paint", "Shipping"): 25, ("Storage", "Assembly"): 15,
                 ("Assembly", "Shipping"): 20}


def flow_frame(names):
    df = pd.DataFrame(0.0, index=names, columns=names)
    for (a, b), v in DEFAULT_FLOWS.items():
        if a in names and b in names:
            df.loc[a, b] = v
    return df


def layout_fig(res, show_flows=True, top_n=8):
    names, R, W, H = res["names"], np.array(res["R"]), res["W"], res["H"]
    F = np.array(res["flow"])
    colors = px.colors.qualitative.Set3
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=W, y1=H, line=dict(width=3))
    for i, nm in enumerate(names):
        x, y, w, h = R[i]
        fig.add_shape(type="rect", x0=x, y0=y, x1=x + w, y1=y + h,
                      fillcolor=colors[i % len(colors)], line=dict(width=1.5), opacity=0.9)
    fig.add_trace(go.Scatter(
        x=R[:, 0] + R[:, 2] / 2, y=R[:, 1] + R[:, 3] / 2, mode="text",
        text=[f"<b>{n}</b><br>{R[i,2]:.1f}×{R[i,3]:.1f}" for i, n in enumerate(names)],
        hovertext=[f"{n}: {R[i,2]*R[i,3]:.0f} sq units" for i, n in enumerate(names)],
        hoverinfo="text", showlegend=False))
    if show_flows:
        pairs = sorted(((F[i, j], i, j) for i in range(len(names)) for j in range(len(names)) if F[i, j] > 0),
                       reverse=True)[:top_n]
        mx = pairs[0][0] if pairs else 1
        for f, i, j in pairs:
            fig.add_annotation(x=R[j, 0] + R[j, 2] / 2, y=R[j, 1] + R[j, 3] / 2,
                               ax=R[i, 0] + R[i, 2] / 2, ay=R[i, 1] + R[i, 3] / 2,
                               xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                               arrowhead=3, arrowwidth=1 + 4 * f / mx, arrowcolor="rgba(200,30,30,0.7)")
    fig.update_xaxes(range=[-1, W + 1], constrain="domain", showgrid=False)
    fig.update_yaxes(range=[-1, H + 1], scaleanchor="x", showgrid=False)
    fig.update_layout(height=620, margin=dict(l=10, r=10, t=10, b=10))
    return fig


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Inputs")
    pname = st.text_input("Run name", "Plant layout v1")
    W = st.number_input("Plot width", 5.0, 1000.0, 40.0)
    H = st.number_input("Plot height", 5.0, 1000.0, 30.0)
    algo = st.selectbox("Algorithm", ["CRAFT (swap)", "Simulated annealing"])
    bands = st.selectbox("Bands (rows)", [0, 1, 2, 3, 4], format_func=lambda v: "auto" if v == 0 else str(v))
    iters = st.slider("Iterations", 100, 10000, 3000, 100)
    max_ar = st.slider("Max aspect ratio", 1.5, 8.0, 4.0, 0.5)
    seed = st.number_input("Seed", 0, 9999, 1)
    run = st.button("Generate layout", type="primary", width="stretch")
    st.caption(f"DB: {db.BACKEND}" + ("" if DB_OK is True else f" ⚠ {DB_OK}"))

st.title("Automated Layout Generator")

t_in, t_lay, t_met, t_saved = st.tabs(["Inputs", "Layout", "Metrics", "Saved runs"])

with t_in:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Departments")
        depts = st.data_editor(DEFAULT_DEPTS, num_rows="dynamic", key="depts", width="stretch")
    depts = depts.dropna()
    depts = depts[depts["name"].astype(str).str.strip() != ""]
    names = depts["name"].astype(str).tolist()
    with c2:
        st.subheader("Flow matrix (from row → to column)")
        flow_df = st.data_editor(flow_frame(names), key=f"flow_{'|'.join(names)}", width="stretch")

if run:
    if len(names) < 2 or len(set(names)) != len(names):
        st.error("Need ≥2 departments with unique names.")
    elif depts["area"].sum() > W * H:
        st.error(f"Total dept area {depts['area'].sum():.0f} > plot area {W*H:.0f}.")
    else:
        F = flow_df.loc[names, names].to_numpy(float)
        with st.spinner("Optimizing..."):
            out = optimize(depts["area"].to_numpy(float), F, W, H, bands, algo, iters, max_ar, int(seed))
        st.session_state["result"] = dict(
            name=pname, algo=algo, names=names, W=W, H=H, R=out["R"].tolist(), flow=F.tolist(),
            areas=depts["area"].tolist(), cost=out["cost"], flow_cost=out["flow_cost"],
            base_cost=out["base_cost"], history=out["history"], bands=out["bands"], max_ar=max_ar)

res = st.session_state.get("result")

with t_lay:
    if not res:
        st.info("Set inputs, then click Generate layout.")
    else:
        show = st.checkbox("Show top flows", True)
        st.plotly_chart(layout_fig(res, show), width="stretch")

with t_met:
    if res:
        R = np.array(res["R"])
        imp = 100 * (res["base_cost"] - res["cost"]) / res["base_cost"] if res["base_cost"] else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total cost", f"{res['cost']:.0f}", f"-{imp:.1f}% vs initial")
        m2.metric("Flow × distance", f"{res['flow_cost']:.0f}")
        m3.metric("Bands used", res["bands"])
        m4.metric("Area stretch", f"{res['W']*res['H']/sum(res['areas']):.2f}×")
        tbl = pd.DataFrame({"dept": res["names"], "req_area": res["areas"],
                            "width": R[:, 2].round(2), "height": R[:, 3].round(2)})
        tbl["actual_area"] = (tbl.width * tbl.height).round(1)
        tbl["aspect"] = np.maximum(tbl.width / tbl.height, tbl.height / tbl.width).round(2)
        tbl["ok"] = tbl.aspect <= res["max_ar"]
        st.dataframe(tbl, width="stretch", hide_index=True)
        st.plotly_chart(px.line(y=res["history"], labels={"x": "step", "y": "cost"}, title="Convergence"),
                        width="stretch")
        hm = pd.DataFrame(res["flow"], index=res["names"], columns=res["names"])
        st.plotly_chart(px.imshow(hm, title="Flow heatmap", color_continuous_scale="Reds"),
                        width="stretch")
        if st.button("Save run to DB"):
            try:
                rid = db.save_run(res["name"], res["algo"], res["cost"],
                                  json.dumps({"W": res["W"], "H": res["H"], "names": res["names"],
                                              "areas": res["areas"], "flow": res["flow"]}),
                                  json.dumps(res))
                st.success(f"Saved run #{rid}")
            except Exception as e:
                st.error(f"DB error: {e}")
    else:
        st.info("No run yet.")

with t_saved:
    try:
        runs = db.list_runs()
    except Exception as e:
        runs = []
        st.error(f"DB error: {e}")
    if not runs:
        st.info("No saved runs.")
    else:
        st.dataframe(pd.DataFrame(runs), width="stretch", hide_index=True)
        rid = st.selectbox("Run id", [r["id"] for r in runs])
        a, b = st.columns(2)
        if a.button("Load"):
            row = db.get_run(rid)
            st.session_state["result"] = json.loads(row["result_json"])
            st.rerun()
        if b.button("Delete"):
            db.delete_run(rid)
            st.rerun()
