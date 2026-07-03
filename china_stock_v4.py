#!/usr/bin/env python3
"""
china_stock_v4.py - 9因子多源选股引擎 (升级版)
从 abu(阿布量化) + maverick-mcp 学习整合
一键运行: python china_stock_v4.py --top 20

因子权重: 价值15% 成长20% 质量15% 技术15% 动量10% 量能5% 波动5% 规模5% 资金10%
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, sys, time, argparse
from datetime import datetime
from pathlib import Path
sys.path.insert(0, '.')

TODAY = datetime.today()

# ── 导入新引擎 ──
try:
    from technicals import full_analysis, score_technical, TechnicalSummary
    from multifactor import full_factor_score, FactorScores
    HAVE_NEW_ENGINE = True
except ImportError:
    HAVE_NEW_ENGINE = False

try:
    from stock_cache import StockCache
    HAVE_CACHE = True
except:
    HAVE_CACHE = False

# ── 股票池 (300只核心A+H) ──
POOL = [
    # AI/科技
    ("002230.SZ","科大讯飞","AI"),("300418.SZ","昆仑万维","AI应用"),("300033.SZ","同花顺","AI金融"),
    ("688111.SS","金山办公","软件/AI"),("688256.SS","寒武纪","AI芯片"),("002049.SZ","紫光国微","半导体"),
    ("603986.SS","兆易创新","半导体"),("688981.SS","中芯国际","半导体"),("002371.SZ","北方华创","半导体设备"),
    ("002475.SZ","立讯精密","消费电子"),("002241.SZ","歌尔股份","声学"),
    # 新能源/汽车
    ("002594.SZ","比亚迪","新能源车"),("300750.SZ","宁德时代","动力电池"),
    ("002460.SZ","赣锋锂业","锂矿"),("300014.SZ","亿纬锂能","锂电池"),
    ("601012.SS","隆基绿能","光伏"),("300274.SZ","阳光电源","光伏逆变器"),
    # 金融
    ("600036.SS","招商银行","银行"),("601318.SS","中国平安","保险"),
    ("600030.SS","中信证券","证券"),("300059.SZ","东方财富","证券"),
    ("601899.SS","紫金矿业","有色/黄金"),("600111.SS","北方稀土","稀土"),
    # 消费/酒
    ("600519.SS","贵州茅台","白酒"),("000858.SZ","五粮液","白酒"),
    ("000568.SZ","泸州老窖","白酒"),("600809.SS","山西汾酒","白酒"),
    ("600887.SS","伊利股份","乳业"),("603288.SS","海天味业","调味品"),
    # 医药
    ("600276.SS","恒瑞医药","创新药"),("603259.SS","药明康德","CXO"),
    ("300760.SZ","迈瑞医疗","医疗器械"),("000538.SZ","云南白药","中药"),
    ("300347.SZ","泰格医药","CXO"),("688180.SS","君实生物","创新药"),
    # 港股
    ("0700.HK","腾讯控股","互联网"),("9988.HK","阿里巴巴","电商"),
    ("9999.HK","网易","游戏"),("3690.HK","美团","本地生活"),
    ("9618.HK","京东","电商"),("9888.HK","百度","AI"),
    ("1810.HK","小米集团","消费电子"),("1211.HK","比亚迪股份","新能源车"),
    ("0388.HK","港交所","交易所"),("1299.HK","友邦保险","保险"),
    ("3968.HK","招商银行H","银行"),("0941.HK","中国移动","通信"),
    ("0883.HK","中国海油","石油"),("1088.HK","中国神华","煤炭"),
    ("2269.HK","药明生物","CXO"),("6862.HK","海底捞","餐饮"),
    # 中特估
    ("601857.SS","中国石油","石油"),("601088.SS","中国神华","煤炭"),
    ("600900.SS","长江电力","电力"),("601728.SS","中国电信","通信"),
    ("600941.SS","中国移动","通信"),("600585.SS","海螺水泥","建材"),
    ("601919.SS","中远海控","航运"),("600019.SS","宝钢股份","钢铁"),
    # 更多中小盘
    ("300896.SZ","爱美客","医美"),("688008.SS","澜起科技","半导体"),
    ("002920.SZ","德赛西威","汽车电子"),("300124.SZ","汇川技术","工控"),
    ("000725.SZ","京东方A","面板"),("002415.SZ","海康威视","安防"),
    ("300274.SZ","阳光电源","光伏"),("601985.SS","中国核电","核电"),
    ("300661.SZ","圣邦股份","芯片"),("688012.SS","中微公司","半导体设备"),
    ("603501.SS","韦尔股份","芯片"),("300782.SZ","卓胜微","射频"),
    ("002916.SZ","深南电路","PCB"),("002938.SZ","鹏鼎控股","PCB"),
    ("601138.SS","工业富联","AI制造"),("300308.SZ","中际旭创","光模块"),
    ("300502.SZ","新易盛","光模块"),("688041.SS","海光信息","AI芯片"),
    ("002230.SZ","科大讯飞","AI"),("688327.SH","云从科技","AI"),
    ("688047.SS","龙芯中科","芯片"),("002555.SZ","三七互娱","游戏"),
    ("300015.SZ","爱尔眼科","医疗"),("300759.SZ","康龙化成","CXO"),
    ("002007.SZ","华兰生物","生物医药"),("300122.SZ","智飞生物","疫苗"),
    ("603392.SS","万泰生物","疫苗"),("600196.SS","复星医药","医药"),
    ("000651.SZ","格力电器","家电"),("000333.SZ","美的集团","家电"),
    ("002352.SZ","顺丰控股","物流"),("601111.SS","中国国航","航空"),
    ("600029.SS","南方航空","航空"),("601006.SS","大秦铁路","铁路"),
    ("600104.SS","上汽集团","汽车"),("000625.SZ","长安汽车","汽车"),
    ("601633.SS","长城汽车","汽车"),("002466.SZ","天齐锂业","锂矿"),
    ("300450.SZ","先导智能","锂电设备"),("601689.SS","拓普集团","汽车零部件"),
    ("300413.SZ","芒果超媒","传媒"),("002602.SZ","世纪华通","游戏"),
    ("300058.SZ","蓝色光标","营销"),("002027.SZ","分众传媒","传媒"),
    ("300773.SZ","拉卡拉","支付"),("000997.SZ","新大陆","数字支付"),
    ("002152.SZ","广电运通","数币"),("600570.SS","恒生电子","金融IT"),
]

def get_data(cache, symbols, force_offline=False):
    """获取数据"""
    t0 = time.time()
    if HAVE_CACHE and cache:
        cache_result = cache.get_data(symbols, force_offline=force_offline, batch_size=30)
        # cache.get_data returns (data_dict, intraday_dict, meta_dict)
        if isinstance(cache_result, tuple) and len(cache_result) >= 1:
            results = cache_result[0]
        else:
            results = cache_result
    else:
        results = {}
        import yfinance as yf
        for sym in symbols:
            try:
                h = yf.Ticker(sym).history(period='6mo')
                if not h.empty:
                    h.columns = [c.lower() for c in h.columns]
                    results[sym] = h
            except:
                pass
    elapsed = time.time() - t0
    return results, elapsed

def print_header():
    """打印表头"""
    print(f"\n{'='*90}")
    print(f"  📊 9因子多源选股  {TODAY.strftime('%Y-%m-%d %H:%M')}")
    print(f"  因子: 价值15% 成长20% 质量15% 技术15% 动量10% 量能5% 波动5% 规模5% 资金10%")
    print(f"  池: {len(POOL)}只")
    print(f"{'='*90}")
    print(f"  {'排名':<4s} {'代码':<12s} {'名称':<10s} {'行业':<10s} {'总分':>5s} {'价值':>5s} {'成长':>5s} {'质量':>5s} {'技术':>5s} {'动量':>5s} {'趋势':>6s} {'RSI':>5s}")
    print(f"  {'─'*4} {'─'*12} {'─'*10} {'─'*10} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*5} {'─'*6} {'─'*5}")

def print_row(rank, code, name, sector, fs, ts):
    """打印一行结果"""
    trend_icon = {"uptrend":"📈","weak_uptrend":"↗","sideways":"➡","weak_downtrend":"↘","downtrend":"📉","unknown":"❓"}
    rsi_str = f"{ts.rsi.value:.0f}{'⚠' if ts.rsi.signal=='overbought' else '⬇' if ts.rsi.signal=='oversold' else ''}" if ts.rsi else "?"
    print(f"  {rank:<4d} {code:<12s} {name:<10s} {sector:<10s} {fs.total:>5.0f} {fs.value:>5.0f} {fs.growth:>5.0f} {fs.quality:>5.0f} {fs.technical:>5.0f} {fs.momentum:>5.0f} {trend_icon.get(ts.trend,'➡'):>6s} {rsi_str:>5s}")

def run_screening(top_n=20, force_offline=False):
    """主筛选流程"""
    if not HAVE_NEW_ENGINE:
        print("❌ 需要 technicals.py 和 multifactor.py，请确保文件存在")
        return
    
    cache = StockCache() if HAVE_CACHE else None
    symbols = [p[0] for p in POOL]
    
    print_header()
    
    # 获取数据
    raw_results, elapsed = get_data(cache, symbols, force_offline)
    results = {}
    for k, df in raw_results.items():
        if df is not None and not df.empty:
            df.columns = [c.lower() for c in df.columns]
            results[k] = df
    
    # 评分
    scored = []
    errors = 0
    for code, name, sector in POOL:
        df = results.get(code)
        if df is None or df.empty:
            errors += 1
            continue
        
        # 使用新引擎评分
        try:
            # 尝试从info获取财务数据 (如果有的话)
            fs, ts = full_factor_score(code, df)
            scored.append((fs.total, code, name, sector, fs, ts))
        except Exception as e:
            errors += 1
            continue
    
    # 排序
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # 打印结果
    for i, (total, code, name, sector, fs, ts) in enumerate(scored[:top_n], 1):
        print_row(i, code, name, sector, fs, ts)
    
    # 输出统计
    print(f"\n  ✅ 成功: {len(scored)}  |  ❌ 失败: {errors}  |  ⏱ {elapsed:.0f}s")
    
    # Top 3 详细分析
    print(f"\n{'─'*90}")
    print(f"  📝 Top 3 详细分析")
    print(f"{'─'*90}")
    
    for i, (total, code, name, sector, fs, ts) in enumerate(scored[:3], 1):
        print(f"\n  #{i} {name} ({code}) [{sector}]  总分:{total:.0f}")
        print(f"     价值{fs.value:.0f} 成长{fs.growth:.0f} 质量{fs.quality:.0f} 技术{fs.technical:.0f}")
        print(f"     动量{fs.momentum:.0f} 量能{fs.volume:.0f} 波动{fs.volatility:.0f} 规模{fs.scale:.0f} 资金{fs.capital:.0f}")
        if ts.rsi: print(f"     RSI:{ts.rsi.value:.1f}({ts.rsi.signal})  MACD:{ts.macd.signal_type}")
        if ts.bollinger: print(f"     布林带:{(ts.bollinger.position*100):.0f}%位置  带宽:{ts.bollinger.bandwidth:.2f}")
        print(f"     ATR:{ts.atr_pct:.1f}%  趋势:{ts.trend}  量比:{ts.volume.volume_ratio:.1f}" if ts.volume else f"     ATR:{ts.atr_pct:.1f}%  趋势:{ts.trend}")
    
    # 保存
    out_path = Path.home() / ".stock_selector_cache"
    out_path.mkdir(exist_ok=True)
    csv_path = out_path / f"selector_{TODAY.strftime('%Y%m%d_%H%M')}.csv"
    rows = []
    for total, code, name, sector, fs, ts in scored:
        rows.append({
            "code": code, "name": name, "sector": sector, "total": total,
            "value": fs.value, "growth": fs.growth, "quality": fs.quality,
            "technical": fs.technical, "momentum": fs.momentum, "volume": fs.volume,
            "volatility": fs.volatility, "scale": fs.scale, "capital": fs.capital,
            "rsi": ts.rsi.value if ts.rsi else 0, "trend": ts.trend,
            "atr_pct": round(ts.atr_pct, 1)
        })
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"\n💾 已保存: {csv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="9因子多源选股引擎")
    parser.add_argument("--top", type=int, default=20, help="展示前N只")
    parser.add_argument("--offline", action="store_true", help="强制离线模式")
    args = parser.parse_args()
    run_screening(top_n=args.top, force_offline=args.offline)
