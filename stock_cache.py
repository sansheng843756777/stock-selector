"""
stock_cache.py - 简易版离线缓存 (for Codespace)
功能: SQLite 缓存 + 多源数据获取 (yfinance + akshare)
"""
import sqlite3, time, warnings
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

CACHE_DIR = Path.home() / ".stock_cache"
CACHE_DIR.mkdir(exist_ok=True)
DB_PATH = CACHE_DIR / "cache.db"

warnings.filterwarnings("ignore")

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY(symbol,date));
CREATE TABLE IF NOT EXISTS cache_meta (
    symbol TEXT PRIMARY KEY, daily_updated TEXT, daily_count INT DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_daily_sym ON daily_prices(symbol,date);
"""

class StockCache:
    def __init__(self):
        self._init_db()
        self._daily = {}

    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(SCHEMA); conn.commit(); conn.close()

    def save_daily(self, symbol, df):
        if df.empty: return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(str(DB_PATH))
        rows = [(symbol, str(df.index[i].date()),
                 float(df.iloc[i].get("open",0)), float(df.iloc[i].get("high",0)),
                 float(df.iloc[i].get("low",0)), float(df.iloc[i]["close"]),
                 float(df.iloc[i].get("volume",0))) for i in range(len(df))]
        conn.executemany("INSERT OR REPLACE INTO daily_prices VALUES(?,?,?,?,?,?,?)", rows)
        conn.execute("INSERT OR REPLACE INTO cache_meta VALUES(?,?,?)", (symbol, now, len(df)))
        conn.commit(); conn.close()
        self._daily[symbol] = df

    def load_daily(self, symbol):
        if symbol in self._daily: return self._daily[symbol]
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute("SELECT date,open,high,low,close,volume FROM daily_prices WHERE symbol=? ORDER BY date", (symbol,)).fetchall()
        conn.close()
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["date","open","high","low","close","volume"])
        df["date"] = pd.to_datetime(df["date"]); df.set_index("date", inplace=True)
        self._daily[symbol] = df; return df

    def get_freshness(self, symbol):
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute("SELECT daily_updated,daily_count FROM cache_meta WHERE symbol=?", (symbol,)).fetchone()
        conn.close()
        if not row: return {"daily":"none","age_days":999,"daily_count":0}
        age = 999
        if row[0]:
            try: age = (datetime.now()-datetime.strptime(row[0][:19],"%Y-%m-%d %H:%M:%S")).days
            except: pass
        f = "fresh" if age<=1 else "recent" if age<=5 else "stale" if age<=20 else "ancient"
        return {"daily":f,"age_days":age,"daily_count":row[1] or 0}

    def get_data(self, symbols, force_offline=False, batch_size=30, progress_cb=None):
        online = self._check_network() and not force_offline
        daily_data = {}; intra_data = {}; meta = {}
        if online:
            import yfinance as yf
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i+batch_size]
                try:
                    df = yf.download(batch, period="3mo", progress=False, group_by="ticker", auto_adjust=True)
                    for t in batch:
                        try:
                            if isinstance(df.columns, pd.MultiIndex) and t in df.columns.get_level_values(0):
                                s = df.xs(t, level=0, axis=1).dropna(how="all")
                            else: continue
                            if s.empty or "Close" not in s.columns: continue
                            out = pd.DataFrame({"close":s["Close"].values,"high":s["High"].values if "High" in s.columns else s["Close"].values,"low":s["Low"].values if "Low" in s.columns else s["Close"].values,"volume":s["Volume"].values if "Volume" in s.columns else np.ones(len(s))}, index=s.index)
                            daily_data[t] = out; self.save_daily(t, out)
                        except: continue
                except: pass
                if progress_cb: progress_cb(min(i+batch_size, len(symbols)), len(symbols))
        for sym in symbols:
            m = meta.get(sym, {})
            if sym not in daily_data or daily_data[sym].empty:
                cached = self.load_daily(sym)
                if not cached.empty:
                    daily_data[sym] = cached
                    m["source"] = "cache"
                    m.update(self.get_freshness(sym))
                else: m["source"] = "none"
            else:
                m["source"] = "online"; m["daily"] = "fresh"; m["age_days"] = 0
            meta[sym] = m
        return daily_data, intra_data, meta

    def _check_network(self, timeout=2):
        import socket
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except: return False

def is_online(): return StockCache()._check_network()
def freshness_icon(f): return {"fresh":"🟢今日","recent":"🟡近日","stale":"🟠陈旧","ancient":"🔴过期","none":"⚫无"}.get(f,"⚫")
