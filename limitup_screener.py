#!/usr/bin/env python3
"""
limitup_screener.py - 连板追涨+八字9因子 综合扫描器
周一开盘前运行: python limitup_screener.py
"""
import warnings; warnings.filterwarnings("ignore")
import sys, os
sys.path.insert(0, os.path.expanduser("~/my-codespace"))
from datetime import datetime
from pathlib import Path

from stock_cache import StockCache
from limitup import batch_scan_limitup, print_limitup_report, LimitUpSignal
from technicals import full_analysis, score_technical
from multifactor import full_factor_score

# ── 五行映射 ──
HETU = {"1":"水","2":"木","3":"火","4":"火","5":"土","6":"水","7":"金","8":"金","9":"水","0":"土"}
INDUSTRY_WUXING = {
    "证券":"金","银行":"金","保险":"金","有色/黄金":"金","有色金属":"金",
    "钢铁":"金","汽车":"金","汽车零部件":"金","金融IT":"金","PCB":"金",
    "白酒":"水","航运":"水","航空":"水","传媒":"水","互联网":"水",
    "AI":"水","AI应用":"水","AI金融":"水","AI芯片":"水","半导体":"水",
    "芯片":"水","消费电子":"水","通信":"水","游戏":"水","软件/AI":"水",
    "电商":"水","本地生活":"水","酒":"水","CXO":"水",
}

WATCHLIST = [
    # 代码, 名称, 行业
    ("688256.SS","寒武纪","AI芯片"),("300418.SZ","昆仑万维","AI应用"),
    ("300059.SZ","东方财富","证券"),("688111.SS","金山办公","软件/AI"),
    ("688008.SS","澜起科技","半导体"),("600030.SS","中信证券","证券"),
    ("601899.SS","紫金矿业","有色/黄金"),("300033.SZ","同花顺","AI金融"),
    ("600570.SS","恒生电子","金融IT"),("002027.SZ","分众传媒","传媒"),
    ("300773.SZ","拉卡拉","支付"),("603986.SS","兆易创新","半导体"),
    ("002049.SZ","紫光国微","半导体"),("002371.SZ","北方华创","半导体设备"),
    ("300661.SZ","圣邦股份","芯片"),("688981.SS","中芯国际","半导体"),
    ("688047.SS","龙芯中科","芯片"),("603501.SS","韦尔股份","芯片"),
    ("300308.SZ","中际旭创","光模块"),("300502.SZ","新易盛","光模块"),
    ("002230.SZ","科大讯飞","AI"),("000858.SZ","五粮液","白酒"),
    ("600519.SS","贵州茅台","白酒"),("601919.SS","中远海控","航运"),
    ("600036.SS","招商银行","银行"),("601318.SS","中国平安","保险"),
    ("000725.SZ","京东方A","面板"),("300750.SZ","宁德时代","动力电池"),
    ("002594.SZ","比亚迪","新能源车"),("600570.SS","恒生电子","金融IT"),
]

def bazi_match(code, sector):
    """八字五行匹配分 0~100"""
    digits = [c for c in code if c.isdigit()]
    last = digits[-1] if digits else "5"
    ce = HETU.get(last, "土")
    ie = INDUSTRY_WUXING.get(sector, "土")
    
    score = 50
    if ce in ("金","水"): score += 30
    if ie in ("金","水"): score += 20
    if ce == "水": score += 5  # 水优先
    return score, ce, ie

def scan():
    cache = StockCache()
    symbols = [t[0] for t in WATCHLIST]
    name_map = {t[0]:t[1] for t in WATCHLIST}
    sector_map = {t[0]:t[2] for t in WATCHLIST}
    
    print(f"\n{'='*100}")
    print(f"  🌟 连板追涨+八字9因子 综合扫描  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  🎯 命主: 甲戌 丙寅 丁丑 庚戌 | 用神金水 | 连板追涨策略")
    print(f"{'='*100}")
    
    # 获取数据
    raw = cache.get_data(symbols)
    if isinstance(raw, tuple): raw = raw[0]
    results = {}
    for k, df in raw.items():
        if df is not None and not df.empty:
            df.columns = [c.lower() for c in df.columns]
            results[k] = df
    
    # 1. 连板扫描
    print("\n📡 扫描涨停信号...")
    signals = batch_scan_limitup(results, name_map)
    
    # 2. 综合评分
    scored = []
    for code, name, sector in WATCHLIST:
        df = results.get(code)
        if df is None or df.empty: continue
        
        # 八字分
        bz, ce, ie = bazi_match(code, sector)
        
        # 技术分
        ts = full_analysis(code, df)
        tech = score_technical(ts)
        
        # 检查是否有涨停信号
        stock_signals = [s for s in signals if s.symbol == code]
        has_limit = any(s.is_limit_up for s in stock_signals)
        max_consec = max((s.consecutive_days for s in stock_signals), default=0)
        limit_score = max((s.quality_score for s in stock_signals), default=0) if stock_signals else 0
        
        # 连板加分
        bonus = 0
        if has_limit: bonus += 20
        if max_consec >= 2: bonus += 15
        if max_consec >= 3: bonus += 10
        bonus += limit_score * 0.2
        
        # 综合
        total = bz * 0.30 + tech * 0.25 + bonus * 0.25 + 50 * 0.20
        
        scored.append((total, code, name, sector, bz, tech, bonus, has_limit, max_consec, ts.rsi.value if ts.rsi else 0, ce, ie))
    
    # 排序: 综合分
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # 打印综合报告
    print(f"\n{'─'*100}")
    print(f"  综合排名 | 连板+八字+9因子")
    print(f"{'─'*100}")
    print(f"  {'排名':<4s} {'代码':<12s} {'名称':<8s} {'行业':<8s} {'综合':>5s} {'八字':>5s} {'技术':>5s} {'连板':>5s} {'连板数':>5s} {'RSI':>5s} {'五行':>6s}")
    print(f"  {'─'*4} {'─'*12} {'─'*8} {'─'*8} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*6}")
    
    for i, (total, code, name, sector, bz, tech, bonus, has_limit, consec, rsi, ce, ie) in enumerate(scored[:15], 1):
        limit_mark = "🚀" if has_limit else "  "
        consec_str = f"{consec}板" if consec > 0 else "-"
        wx_str = f"{ce}{ie}"
        print(f"  {i:<4d} {code:<12s} {name:<8s} {sector:<8s} {total:>5.1f} {bz:>5.0f} {tech:>5.0f} {limit_mark:>4s}{bonus:>4.0f} {consec_str:>5s} {rsi:>5.1f} {wx_str:>6s}")
    
    # 追击建议
    chase = [s for s in signals if "追击" in s.prediction]
    print(f"\n{'═'*100}")
    print(f"  🚀 追击建议 (连板追涨)")
    print(f"{'═'*100}")
    
    if chase:
        print(f"  {'代码':<12s} {'名称':<8s} {'涨幅':>6s} {'类型':<12s} {'连板':>4s} {'评分':>5s} {'八字':>5s} {'建议':>8s}")
        print(f"  {'─'*12} {'─'*8} {'─'*6} {'─'*12} {'─'*4} {'─'*5} {'─'*5} {'─'*8}")
        for s in chase:
            code = s.symbol
            sector = sector_map.get(code, "")
            bz, ce, ie = bazi_match(code, sector)
            bz_mark = "✅" if bz >= 70 else "⚠" if bz >= 50 else "❌"
            consec_str = f"{s.consecutive_days}板" if s.consecutive_days > 1 else "首板"
            print(f"  {s.symbol:<12s} {s.name:<8s} {s.limit_up_pct:>+5.1f}% {s.limit_up_type:<12s} {consec_str:>4s} {s.quality_score:>5.1f} {bz:>4.0f}{bz_mark:>3s} {s.prediction:>8s}")
    else:
        print("  📭 当前无涨停追击信号。市场无明确连板机会。")
        ranked = [s for s in scored if s[8] > 0]  # 有连板历史
        if ranked:
            print(f"\n  📋 近期有连板历史的标的 (可关注二波):")
            for _, code, name, sector, bz, tech, bonus, _, consec, rsi, ce, ie in ranked[:5]:
                print(f"     {code} {name} {sector} 之前{consec}连板 RSI{rsi:.0f}")
        else:
            print(f"  当前池中无连板历史标的")
    
    print(f"\n  💾 扫描完成 | {len(scored)}只评分 | {len(chase)}只追击信号")

if __name__ == "__main__":
    scan()
