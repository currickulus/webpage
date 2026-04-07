print("Starting server...")
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sock import Sock
import json
import time
import MetaTrader5 as mt5
import sqlite3
from datetime import datetime
app = Flask(__name__)
CORS(app)
sock = Sock(app)
SYMBOL = "MYMU26"
TF = mt5.TIMEFRAME_M1
DB_PATH = r"C:\mt5_bridge\bars.db"
mt5.initialize()
mt5.symbol_select(SYMBOL, True)
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bars (
            t INTEGER PRIMARY KEY,
            o REAL, h REAL, l REAL, c REAL, v INTEGER,
            symbol TEXT DEFAULT 'MYMU26'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            t INTEGER,
            score REAL,
            verdict TEXT,
            bull INTEGER,
            bear INTEGER,
            total INTEGER,
            PRIMARY KEY (t)
        )
    ''')
    conn.commit()
    conn.close()
def save_bars(bars):
    conn = get_db()
    conn.executemany('''
        INSERT OR IGNORE INTO bars (t, o, h, l, c, v)
        VALUES (:t, :o, :h, :l, :c, :v)
    ''', bars)
    conn.commit()
    conn.close()
init_db()
@sock.route('/ws')
def ws_feed(ws):
    while True:
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick:
                price = tick.ask if tick.ask > 0 else tick.bid
                ws.send(json.dumps({
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "last": price,
                    "t": int(tick.time * 1000)
                }))
        except Exception as e:
            break
        time.sleep(1)
@app.route("/bars")
def get_bars():
    mt5.symbol_info_tick(SYMBOL)
    rates = mt5.copy_rates_from_pos(SYMBOL, TF, 0, 300)
    if rates is None:
        mt5.initialize()
        mt5.symbol_select(SYMBOL, True)
        rates = mt5.copy_rates_from_pos(SYMBOL, TF, 0, 300)
    if rates is None:
        return jsonify({"error": "No data"}), 500
    bars = [{
        "t": int(b[0]) * 1000,
        "o": float(b[1]),
        "h": float(b[2]),
        "l": float(b[3]),
        "c": float(b[4]),
        "v": int(b[5])
    } for b in rates]
    save_bars([{
        "t": bar["t"],
        "o": bar["o"],
        "h": bar["h"],
        "l": bar["l"],
        "c": bar["c"],
        "v": bar["v"]
    } for bar in bars])
    return jsonify(bars)
@app.route("/seed_history")
def seed_history():
    mt5.symbol_info_tick(SYMBOL)
    rates = mt5.copy_rates_from_pos(SYMBOL, TF, 0, 50000)
    if rates is None:
        return jsonify({"error": "No data"}), 500
    bars = [{
        "t": int(b[0]) * 1000,
        "o": float(b[1]),
        "h": float(b[2]),
        "l": float(b[3]),
        "c": float(b[4]),
        "v": int(b[5])
    } for b in rates]
    save_bars(bars)
    return jsonify({"seeded": len(bars), "oldest": bars[0]["t"], "newest": bars[-1]["t"]})
@app.route("/history")
def get_history():
    limit = request.args.get("limit", 2000, type=int)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM bars ORDER BY t DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in reversed(rows)])
@app.route("/log_signal", methods=["POST"])
def log_signal():
    data = request.json
    conn = get_db()
    conn.execute('''
        INSERT OR REPLACE INTO signals (t, score, verdict, bull, bear, total)
        VALUES (:t, :score, :verdict, :bull, :bear, :total)
    ''', data)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
@app.route("/backtest_report")
def backtest_report():
    conn = get_db()
    bars = conn.execute(
        "SELECT * FROM bars ORDER BY t ASC"
    ).fetchall()
    conn.close()
    bars = [dict(b) for b in bars]
    if len(bars) < 50:
        return jsonify({"error": "Not enough data yet"}), 400
    results = []
    for i in range(20, len(bars) - 5):
        recent_vols = [bars[j]["v"] for j in range(i-20, i)]
        avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else 1
        vol_ratio = bars[i]["v"] / avg_vol if avg_vol else 0
        candle_move = abs(bars[i]["c"] - bars[i]["o"])
        trs = [abs(bars[j]["h"] - bars[j]["l"]) for j in range(i-14, i)]
        atr = sum(trs) / len(trs) if trs else 1
        is_bull = bars[i]["c"] > bars[i]["o"] and vol_ratio > 1.5 and candle_move > atr * 0.5
        is_bear = bars[i]["c"] < bars[i]["o"] and vol_ratio > 1.5 and candle_move > atr * 0.5
        if not is_bull and not is_bear:
            continue
        entry = bars[i]["c"]
        sl = atr * 1.0
        tp = atr * 2.0
        outcome = "timeout"
        pnl = 0
        for j in range(i+1, min(i+6, len(bars))):
            if is_bull:
                if bars[j]["l"] <= entry - sl:
                    outcome = "loss"
                    pnl = -sl * 0.50
                    break
                if bars[j]["h"] >= entry + tp:
                    outcome = "win"
                    pnl = tp * 0.50
                    break
            else:
                if bars[j]["h"] >= entry + sl:
                    outcome = "loss"
                    pnl = -sl * 0.50
                    break
                if bars[j]["l"] <= entry - tp:
                    outcome = "win"
                    pnl = tp * 0.50
                    break
        if outcome == "timeout":
            exit_price = bars[min(i+5, len(bars)-1)]["c"]
            pnl = (exit_price - entry) * 0.50 if is_bull else (entry - exit_price) * 0.50
        hour = datetime.fromtimestamp(bars[i]["t"] / 1000).hour
        results.append({
            "t": bars[i]["t"],
            "dir": "bull" if is_bull else "bear",
            "entry": entry,
            "outcome": outcome,
            "pnl": round(pnl, 2),
            "hour": hour,
            "vol_ratio": round(vol_ratio, 2)
        })
    if not results:
        return jsonify({"error": "No signals found in data"}), 400
    wins = [r for r in results if r["outcome"] == "win"]
    losses = [r for r in results if r["outcome"] == "loss"]
    total_pnl = sum(r["pnl"] for r in results)
    win_rate = len(wins) / len(results) * 100 if results else 0
    by_hour = {}
    for r in results:
        h = r["hour"]
        if h not in by_hour:
            by_hour[h] = {"wins": 0, "losses": 0, "pnl": 0}
        if r["outcome"] == "win":
            by_hour[h]["wins"] += 1
        elif r["outcome"] == "loss":
            by_hour[h]["losses"] += 1
        by_hour[h]["pnl"] = round(by_hour[h]["pnl"] + r["pnl"], 2)
    return jsonify({
        "total_signals": len(results),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(results), 2) if results else 0,
        "by_hour": by_hour,
        "trades": results[-50:]
    })
@app.route("/symbol_info")
def symbol_info():
    info = mt5.symbol_info(SYMBOL)
    if not info:
        return jsonify({}), 404
    return jsonify({"spread": info.spread, "ask": info.ask, "bid": info.bid})
@app.route("/symbols")
def list_symbols():
    symbols = mt5.symbols_get()
    return jsonify([s.name for s in symbols if 'MYM' in s.name.upper()])
if __name__ == "__main__":
    print("Calling app.run...")
    app.run(host="0.0.0.0", port=5050, debug=True, threaded=True)
 
