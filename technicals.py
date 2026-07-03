"""
technicals.py - 技术指标计算引擎
从 maverick-mcp 和 abu 项目提取优化
核心: RSI, MACD, 布林带, 随机指标, 量价分析
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

@dataclass
class RSIData:
    value: float
    period: int
    signal: str  # overbought / oversold / neutral

@dataclass
class MACDData:
    macd: float
    signal: float
    histogram: float
    signal_type: str  # bullish / bearish / crossover

@dataclass
class BollingerData:
    upper: float
    middle: float
    lower: float
    bandwidth: float  # (upper-lower)/middle
    position: float   # 价格在布林带中的位置 0~1

@dataclass
class StochasticData:
    k: float
    d: float
    signal: str

@dataclass
class VolumeData:
    volume_ratio: float  # 当日量/均量
    trend: str           # expanding / contracting / normal

@dataclass
class TechnicalSummary:
    symbol: str
    rsi: Optional[RSIData] = None
    macd: Optional[MACDData] = None
    bollinger: Optional[BollingerData] = None
    stochastic: Optional[StochasticData] = None
    volume: Optional[VolumeData] = None
    atr_pct: float = 0.0
    trend: str = "unknown"  # uptrend / downtrend / sideways

def calc_rsi(prices: pd.Series, period: int = 14) -> RSIData:
    if len(prices) < period:
        return RSIData(50.0, period, "neutral")
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    avg_gain = gains.rolling(period).mean()
    avg_loss = losses.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    if val >= 70:
        sig = "overbought"
    elif val <= 30:
        sig = "oversold"
    else:
        sig = "neutral"
    return RSIData(val, period, sig)

def calc_macd(prices: pd.Series, fast=12, slow=26, signal=9) -> MACDData:
    if len(prices) < slow:
        return MACDData(0, 0, 0, "neutral")
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    sig_line = macd_line.ewm(span=signal).mean()
    hist = macd_line - sig_line
    m, s, h = float(macd_line.iloc[-1]), float(sig_line.iloc[-1]), float(hist.iloc[-1])
    if m > s and h > 0 and hist.iloc[-2] <= 0 if len(hist) > 1 else False:
        st = "bullish_crossover"
    elif m < s and h < 0 and hist.iloc[-2] >= 0 if len(hist) > 1 else False:
        st = "bearish_crossover"
    elif m > s:
        st = "bullish"
    elif m < s:
        st = "bearish"
    else:
        st = "neutral"
    return MACDData(m, s, h, st)

def calc_bollinger(prices: pd.Series, period=20, std_dev=2.0) -> BollingerData:
    if len(prices) < period:
        return BollingerData(0, float(prices.iloc[-1]), 0, 0, 0.5)
    middle = float(prices.rolling(period).mean().iloc[-1])
    std = float(prices.rolling(period).std().iloc[-1])
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    cur = float(prices.iloc[-1])
    bandwidth = (upper - lower) / middle if middle != 0 else 0
    if upper != lower:
        pos = (cur - lower) / (upper - lower)
    else:
        pos = 0.5
    return BollingerData(upper, middle, lower, bandwidth, pos)

def calc_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> StochasticData:
    if len(close) < period:
        return StochasticData(50, 50, "neutral")
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    d = k.rolling(3).mean()
    kv, dv = float(k.iloc[-1]), float(d.iloc[-1])
    if kv > 80:
        sig = "overbought"
    elif kv < 20:
        sig = "oversold"
    else:
        sig = "neutral"
    return StochasticData(kv, dv, sig)

def calc_volume_analysis(volume: pd.Series, period=20) -> VolumeData:
    if len(volume) < period:
        return VolumeData(1.0, "normal")
    avg = float(volume.rolling(period).mean().iloc[-1])
    cur = float(volume.iloc[-1])
    ratio = cur / avg if avg > 0 else 1.0
    if ratio > 1.5:
        trend = "expanding"
    elif ratio < 0.5:
        trend = "contracting"
    else:
        trend = "normal"
    return VolumeData(ratio, trend)

def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> float:
    if len(close) < 2:
        return 0.0
    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)
    atr = tr.rolling(period).mean()
    return float(atr.iloc[-1]) if not atr.empty and not np.isnan(atr.iloc[-1]) else 0.0

def calc_trend(close: pd.Series, ma_short=10, ma_long=30) -> str:
    if len(close) < ma_long:
        return "unknown"
    ma_s = close.rolling(ma_short).mean().iloc[-1]
    ma_l = close.rolling(ma_long).mean().iloc[-1]
    cur = close.iloc[-1]
    if cur > ma_s and ma_s > ma_l:
        return "uptrend"
    elif cur < ma_s and ma_s < ma_l:
        return "downtrend"
    elif cur > ma_l:
        return "weak_uptrend"
    elif cur < ma_l:
        return "weak_downtrend"
    return "sideways"

def full_analysis(symbol: str, df: pd.DataFrame) -> TechnicalSummary:
    """对一只股票做完整技术分析"""
    close = df['Close'] if 'Close' in df.columns else df['close']
    high = df['High'] if 'High' in df.columns else df['high']
    low = df['Low'] if 'Low' in df.columns else df['low']
    vol = df['Volume'] if 'Volume' in df.columns else df['volume']
    
    ts = TechnicalSummary(symbol=symbol)
    ts.rsi = calc_rsi(close)
    ts.macd = calc_macd(close)
    ts.bollinger = calc_bollinger(close)
    ts.stochastic = calc_stochastic(high, low, close)
    ts.volume = calc_volume_analysis(vol)
    ts.atr_pct = calc_atr(high, low, close) / float(close.iloc[-1]) * 100 if float(close.iloc[-1]) > 0 else 0
    ts.trend = calc_trend(close)
    return ts

def score_technical(ts: TechnicalSummary) -> float:
    """技术面综合评分 0~100"""
    score = 50.0
    # RSI
    if ts.rsi:
        if ts.rsi.signal == "oversold": score += 15
        elif ts.rsi.signal == "overbought": score -= 10
        elif 40 <= ts.rsi.value <= 60: score += 5
    # MACD
    if ts.macd:
        if ts.macd.signal_type == "bullish_crossover": score += 20
        elif ts.macd.signal_type == "bullish": score += 10
        elif ts.macd.signal_type == "bearish_crossover": score -= 15
        elif ts.macd.signal_type == "bearish": score -= 5
    # 布林带
    if ts.bollinger:
        if ts.bollinger.position < 0.2: score += 10  # 下轨附近=超卖
        elif ts.bollinger.position > 0.8: score -= 5  # 上轨附近=超买
    # 量能
    if ts.volume:
        if ts.volume.trend == "expanding": score += 5
        elif ts.volume.trend == "contracting": score -= 5
    # 趋势
    if ts.trend == "uptrend": score += 10
    elif ts.trend == "downtrend": score -= 10
    # ATR
    if ts.atr_pct > 5: score += 5  # 高波动适合短线
    
    return max(0, min(100, score))
