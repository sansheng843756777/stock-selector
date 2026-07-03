#!/usr/bin/env python3
"""
dashboard.py - Streamlit 选股看板
运行: streamlit run dashboard.py
"""
import streamlit as st, subprocess, os, json, pandas as pd, numpy as np
from datetime import datetime

st.set_page_config(page_title="股票量化分析", layout="wide")
st.title("📊 中国股市多因子选股看板")
st.caption(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

col1, col2, col3 = st.columns(3)
col1.metric("A股数量", "~5000", "含北交所")
col2.metric("港股数量", "~2500", "含主板")
col3.metric("模型因子", "9大类", "40+细分")

if st.button("🚀 运行选股模型", type="primary"):
    with st.spinner("正在获取行情数据..."):
        r = subprocess.run(["python","china_stock_v3.py"], capture_output=True, text=True, timeout=120)
        st.text(r.stdout)
        if r.returncode == 0:
            st.success("选股完成!")
        else:
            st.error(f"错误: {r.stderr}")

st.subheader("📝 快速分析个股")
sym = st.text_input("输入股票代码 (如 688111.SS / 000858.SZ / 0700.HK)")
if sym:
    import yfinance as yf
    with st.spinner("获取数据..."):
        tk = yf.Ticker(sym)
        info = tk.info or {}
        h = tk.history(period="3mo")
        if not h.empty:
            c = h["Close"].values
            cur = info.get("currentPrice") or c[-1]
            pe = info.get("trailingPE","N/A")
            mc = info.get("marketCap",0)
            st.write(f"**{info.get('longName',sym)}** | 现价: {cur:.2f} | PE: {pe} | 市值: {mc/1e8:.0f}亿")
            st.line_chart(h["Close"])
        else:
            st.error("未找到该股票")
