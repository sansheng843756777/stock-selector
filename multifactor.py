"""
multifactor.py - 多因子选股增强版
从 abu (阿布量化) 和 maverick-mcp 项目学习整合

因子体系:
  1. 价值因子 (PE, PB, PS)
  2. 成长因子 (营收增长, 利润增长)
  3. 质量因子 (ROE, 毛利率, 净利率)
  4. 技术因子 (RSI, MACD, 布林带)
  5. 动量因子 (近N日涨幅)
  6. 量能因子 (成交量变化)
  7. 波动因子 (ATR)
  8. 规模因子 (市值)
  9. 资金因子 (换手率)
"""
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from dataclasses import dataclass
from technicals import full_analysis, score_technical, TechnicalSummary

@dataclass
class FactorScores:
    value: float = 50.0    # 价值
    growth: float = 50.0   # 成长
    quality: float = 50.0  # 质量
    technical: float = 50.0  # 技术
    momentum: float = 50.0 # 动量
    volume: float = 50.0   # 量能
    volatility: float = 50.0  # 波动
    scale: float = 50.0    # 规模
    capital: float = 50.0  # 资金
    
    @property
    def total(self) -> float:
        """加权总分"""
        w = {
            'value': 0.15, 'growth': 0.20, 'quality': 0.15,
            'technical': 0.15, 'momentum': 0.10, 'volume': 0.05,
            'volatility': 0.05, 'scale': 0.05, 'capital': 0.10
        }
        return sum(getattr(self, k) * v for k, v in w.items())
    
    @property
    def breakdown(self) -> str:
        parts = [f"{k}={getattr(self,k):.0f}" for k in ['value','growth','quality','technical','momentum','volume','volatility','scale','capital']]
        return f"总分{self.total:.0f} | " + " ".join(parts)

def score_value(pe: Optional[float], pb: Optional[float], ps: Optional[float] = None) -> float:
    """价值因子评分"""
    score = 50.0
    if pe and pe > 0:
        if pe < 10: score = 80
        elif pe < 15: score = 70
        elif pe < 25: score = 55
        elif pe < 50: score = 40
        else: score = 25
    if pb and pb > 0:
        if pb < 1.5: score += 10
        elif pb < 3: score += 5
        elif pb > 10: score -= 10
    return max(0, min(100, score))

def score_growth(revenue_growth: Optional[float], profit_growth: Optional[float] = None) -> float:
    """成长因子评分"""
    score = 50.0
    if revenue_growth:
        if revenue_growth > 50: score += 30
        elif revenue_growth > 30: score += 20
        elif revenue_growth > 15: score += 10
        elif revenue_growth > 5: score += 3
        elif revenue_growth < -10: score -= 15
    if profit_growth:
        if profit_growth > 100: score += 20
        elif profit_growth > 30: score += 10
        elif profit_growth < -20: score -= 15
    return max(0, min(100, score))

def score_quality(roe: Optional[float], gross_margin: Optional[float], net_margin: Optional[float]) -> float:
    """质量因子评分"""
    score = 50.0
    if roe:
        if roe > 30: score += 25
        elif roe > 20: score += 15
        elif roe > 15: score += 10
        elif roe > 10: score += 5
        elif roe < 5: score -= 10
    if gross_margin:
        if gross_margin > 70: score += 15
        elif gross_margin > 50: score += 10
        elif gross_margin > 30: score += 5
        elif gross_margin < 15: score -= 5
    if net_margin:
        if net_margin > 20: score += 10
        elif net_margin > 10: score += 5
        elif net_margin < 0: score -= 10
    return max(0, min(100, score))

def score_momentum(close: pd.Series, periods=[5, 20, 60]) -> float:
    """动量因子评分"""
    if len(close) < max(periods):
        return 50.0
    score = 50.0
    cur = float(close.iloc[-1])
    for p in periods:
        prev = float(close.iloc[-p-1]) if len(close) > p else None
        if prev and prev > 0:
            ret = (cur / prev - 1) * 100
            if p == 5:
                if ret > 15: score += 15
                elif ret > 8: score += 10
                elif ret > 3: score += 5
                elif ret < -8: score -= 10
            elif p == 20:
                if ret > 30: score += 10
                elif ret > 15: score += 5
                elif ret < -15: score -= 5
            elif p == 60:
                if ret > 50: score += 5
                elif ret > 20: score += 3
                elif ret < -20: score -= 5
    return max(0, min(100, score))

def score_scale(market_cap: Optional[float]) -> float:
    """规模因子 - 小盘股弹性大"""
    if market_cap is None:
        return 50.0
    cap_b = market_cap / 1e8  # 转亿
    if cap_b < 50: return 70   # 极小盘
    elif cap_b < 100: return 65
    elif cap_b < 300: return 55
    elif cap_b < 1000: return 45
    elif cap_b < 5000: return 35
    else: return 25

def score_capital(turnover_rate: Optional[float]) -> float:
    """资金因子 - 换手率"""
    if turnover_rate is None:
        return 50.0
    if turnover_rate > 15: return 70
    elif turnover_rate > 8: return 60
    elif turnover_rate > 3: return 50
    elif turnover_rate > 1: return 40
    else: return 30

def full_factor_score(
    symbol: str,
    price_df: pd.DataFrame,
    pe: Optional[float] = None,
    pb: Optional[float] = None,
    roe: Optional[float] = None,
    gross_margin: Optional[float] = None,
    net_margin: Optional[float] = None,
    revenue_growth: Optional[float] = None,
    profit_growth: Optional[float] = None,
    market_cap: Optional[float] = None,
    turnover_rate: Optional[float] = None
) -> tuple[FactorScores, TechnicalSummary]:
    """完整的9因子评分"""
    fs = FactorScores()
    ts = full_analysis(symbol, price_df)
    
    fs.value = score_value(pe, pb)
    fs.growth = score_growth(revenue_growth, profit_growth)
    fs.quality = score_quality(roe, gross_margin, net_margin)
    fs.technical = score_technical(ts)
    
    close = price_df['Close'] if 'Close' in price_df.columns else price_df['close']
    fs.momentum = score_momentum(close)
    
    fs.scale = score_scale(market_cap)
    fs.capital = score_capital(turnover_rate)
    
    # 波动因子
    if ts.atr_pct > 8: fs.volatility = 70
    elif ts.atr_pct > 5: fs.volatility = 60
    elif ts.atr_pct > 3: fs.volatility = 50
    else: fs.volatility = 40
    
    # 量能因子
    if ts.volume:
        if ts.volume.trend == "expanding": fs.volume = 65
        elif ts.volume.trend == "contracting": fs.volume = 40
        else: fs.volume = 50
    
    return fs, ts
