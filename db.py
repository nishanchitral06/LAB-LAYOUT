"""Turso (HTTP API) if env vars set, else local SQLite fallback for dev."""
import os
import sqlite3
import requests

URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
LOCAL = os.getenv("LOCAL_DB", "layouts.db")
BACKEND = "turso" if URL else "local sqlite"


def _arg(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}


def _val(c):
    t = c.get("type")
    if t == "null":
        return None
    if t == "integer":
        return int(c["value"])
    if t == "float":
        return float(c["value"])
    return c.get("value")


def execute(sql, args=()):
    """Return (rows as list[dict], last_insert_id)."""
    if URL:
        base = URL.replace("libsql://", "https://").rstrip("/")
        body = {"requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in args]}},
            {"type": "close"}]}
        r = requests.post(f"{base}/v2/pipeline", json=body, timeout=20,
                          headers={"Authorization": f"Bearer {TOKEN}"})
        r.raise_for_status()
        res = r.json()["results"][0]
        if res["type"] == "error":
            raise RuntimeError(res["error"]["message"])
        out = res["response"]["result"]
        cols = [c["name"] for c in out["cols"]]
        rows = [{k: _val(v) for k, v in zip(cols, row)} for row in out["rows"]]
        lid = out.get("last_insert_rowid")
        return rows, int(lid) if lid else None
    con = sqlite3.connect(LOCAL)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, tuple(args))
        rows = [dict(r) for r in cur.fetchall()]
        con.commit()
        return rows, cur.lastrowid
    finally:
        con.close()


def init():
    execute("""CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, algorithm TEXT, cost REAL,
        inputs_json TEXT, result_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")


def save_run(name, algorithm, cost, inputs_json, result_json):
    return execute("INSERT INTO runs (name, algorithm, cost, inputs_json, result_json) VALUES (?,?,?,?,?)",
                   (name, algorithm, cost, inputs_json, result_json))[1]


def list_runs():
    return execute("SELECT id, name, algorithm, cost, created_at FROM runs ORDER BY id DESC LIMIT 50")[0]


def get_run(run_id):
    rows = execute("SELECT * FROM runs WHERE id = ?", (run_id,))[0]
    return rows[0] if rows else None


def delete_run(run_id):
    execute("DELETE FROM runs WHERE id = ?", (run_id,))
