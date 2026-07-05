"""
limitup.py - 连板追涨策略引擎
从 Quant-Strategy-for-Consecutive-Limit-Up-Stocks 学习整合
核心: 识别涨停信号→评分→预测连板概率

适配日线数据（yfinance/akshare），无需分钟级数据
"""
import numpy as np
import pandas as pd
from typing import Optional
from dataclasses import dataclass

@dataclass
class LimitUpSignal:
    """涨停信号"""
    symbol: str
    name: str
    date: str
    close: float
    limit_up_pct: float        # 当日涨幅
    is_limit_up: bool          # 是否涨停
    limit_up_type: str         # 主板10% / 科创20% / 创业20% / 北交30%
    consecutive_days: int      # 连板天数
    volume_ratio: float        # 量比
    turnover_rate: float       # 换手率
    board_position: float      # 封板力度 (0~1, 基于量价估算)
    market_hot: float          # 板块热度 (基于同行业涨停数)
    quality_score: float       # 综合质量评分 0~100
    prediction: str            # 建议: 追击/观望/放弃

def detect_limit_up(df: pd.DataFrame, code: str = "") -> list[LimitUpSignal]:
    """
    从日线数据检测涨停信号
    
    Args:
        df: DataFrame with columns [close, high, low, volume]
        code: 股票代码（用于判断涨跌幅限制）
    
    Returns:
        涨停信号列表（最近5个交易日）
    """
    if df.empty or len(df) < 3:
        return []
    
    # 判断涨跌幅限制
    if code.endswith(('.SZ','.SS')):
        if code.startswith('30'): limit = 0.20   # 创业板
        elif code.startswith('68'): limit = 0.20  # 科创板
        elif code.startswith('8'): limit = 0.30   # 北交所
        elif code.startswith('4'): limit = 0.30   # 新三板
        else: limit = 0.10                         # 主板
    elif code.endswith('.HK'):
        limit = None  # 港股无涨跌幅限制
    else:
        limit = 0.10  # 默认主板
    
    close = df['close'].values
    volume = df['volume'].values if 'volume' in df.columns else np.ones_like(close)
    high = df['high'].values if 'high' in df.columns else close
    low = df['low'].values if 'low' in df.columns else close
    
    signals = []
    
    for i in range(2, len(close)):
        if np.isnan(close[i]) or np.isnan(close[i-1]):
            continue
        
        # 当日涨幅
        pct = (close[i] / close[i-1] - 1)
        
        # 判断是否触及涨停
        is_limit = False
        up_type = ""
        if limit and pct >= limit * 0.95:  # 接近涨停
            is_limit = True
            if limit >= 0.20:
                up_type = "科创/创业板20%"
            elif limit >= 0.30:
                up_type = "北交所30%"
            else:
                up_type = "主板10%"
        
        # 计算连板天数
        consec = 1
        for j in range(i-1, max(0, i-5), -1):
            if not np.isnan(close[j]) and not np.isnan(close[j-1]):
                prev_pct = (close[j] / close[j-1] - 1)
                if prev_pct >= (limit * 0.95 if limit else 0.095):
                    consec += 1
                else:
                    break
        
        # 量比（相对20日均量）
        vol_avg = np.mean(volume[max(0, i-20):i]) if i >= 20 else np.mean(volume[:i])
        vol_ratio = volume[i] / vol_avg if vol_avg > 0 else 1.0
        
        # 换手率估算
        turnover = min(50, vol_ratio * 3)  # 粗略估算
        
        # 封板力度估算
        # 基于: 高开幅度小+量比适中+收盘在高位 = 封板强
        open_pct = (close[i] / close[i-1] - 1) if i > 0 else 0
        intraday_range = (high[i] - low[i]) / close[i-1] if close[i-1] > 0 else 0
        close_position = (close[i] - low[i]) / (high[i] - low[i]) if (high[i] - low[i]) > 0 else 0.5
        
        board = 0.5
        if is_limit:
            board = 0.6
            if close_position > 0.95: board += 0.2  # 封死涨停
            if vol_ratio < 0.8: board += 0.1         # 缩量涨停=强
            if consec >= 2: board += 0.1              # 连板加分
            board = min(1.0, board)
        
        # 质量评分
        score = 50.0
        if is_limit:
            score += 20                              # 涨停基础分
            if consec >= 2: score += 15               # 连板加分
            if consec >= 4: score += 10               # 妖股加分
            if vol_ratio < 0.5: score += 10           # 缩量涨停=强
            elif vol_ratio < 1.0: score += 5
            elif vol_ratio > 3: score -= 10            # 巨量=分歧
            if board > 0.8: score += 10               # 封板强
            if open_pct < 0.03: score += 5             # 低开涨停=超预期
        score = max(0, min(100, score))
        
        # 预测
        if is_limit and score >= 70:
            pred = "🔥追击"
        elif is_limit and score >= 50:
            pred = "⚠观望"
        elif is_limit:
            pred = "❌放弃"
        elif consec >= 2:
            pred = "⏳连板中"
        else:
            pred = "⬜正常"
        
        sig = LimitUpSignal(
            symbol=code,
            name="",
            date=str(pd.to_datetime(df.index[i]).strftime('%Y-%m-%d')) if hasattr(df.index, 'strftime') else str(df.index[i]),
            close=float(close[i]),
            limit_up_pct=float(pct * 100),
            is_limit_up=is_limit,
            limit_up_type=up_type if is_limit else "-",
            consecutive_days=consec,
            volume_ratio=round(vol_ratio, 2),
            turnover_rate=round(turnover, 1),
            board_position=round(board, 2),
            market_hot=0.0,
            quality_score=round(score, 1),
            prediction=pred
        )
        signals.append(sig)
    
    # 只返回最近5天且有信号的
    recent = [s for s in signals[-10:] if s.is_limit_up or s.consecutive_days >= 2]
    return recent[-5:] if recent else signals[-3:]

def batch_scan_limitup(data_dict: dict[str, pd.DataFrame], 
                       name_map: dict[str, str] = None) -> list[LimitUpSignal]:
    """
    批量扫描全池涨停信号
    
    Args:
        data_dict: {code: DataFrame} 格式的数据
        name_map: {code: name} 名称映射
    
    Returns:
        按质量排序的涨停信号列表
    """
    all_signals = []
    
    for code, df in data_dict.items():
        if df is None or df.empty:
            continue
        signals = detect_limit_up(df, code)
        if signals:
            name = name_map.get(code, "") if name_map else ""
            for s in signals:
                s.name = name
            all_signals.extend(signals)
    
    # 排序: 涨停优先 连板优先 质量优先
    all_signals.sort(key=lambda s: (
        s.is_limit_up,
        s.consecutive_days >= 2,
        s.quality_score
    ), reverse=True)
    
    return all_signals

def print_limitup_report(signals: list[LimitUpSignal], top_n: int = 10):
    """打印涨停追踪报告"""
    print(f"\n{'='*90}")
    print(f"  🚀 连板追涨雷达  {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*90}")
    print(f"  {'代码':<12s} {'名称':<8s} {'日期':<12s} {'涨幅':>6s} {'类型':<12s} {'连板':>4s} {'量比':>5s} {'封板':>5s} {'评分':>5s} {'建议':>8s}")
    print(f"  {'─'*12} {'─'*8} {'─'*12} {'─'*6} {'─'*12} {'─'*4} {'─'*5} {'─'*5} {'─'*5} {'─'*8}")
    
    for s in signals[:top_n]:
        consec_str = f"{s.consecutive_days}板" if s.consecutive_days > 1 else "首板"
        print(f"  {s.symbol:<12s} {s.name:<8s} {s.date:<12s} {s.limit_up_pct:>+5.1f}% {s.limit_up_type:<12s} {consec_str:>4s} {s.volume_ratio:>5.1f} {s.board_position:>5.2f} {s.quality_score:>5.1f} {s.prediction:>8s}")
    
    # 追击建议汇总
    chase = [s for s in signals if "追击" in s.prediction]
    watch = [s for s in signals if "观望" in s.prediction]
    print(f"\n  🔥 追击信号: {len(chase)}只")
    for s in chase[:5]:
        print(f"     {s.symbol} {s.name} {s.consecutive_days}连板 评分{s.quality_score}")
    print(f"  ⚠ 观望信号: {len(watch)}只")
    if not chase:
        print(f"  📭 无追击信号, 市场无明确连板机会")
