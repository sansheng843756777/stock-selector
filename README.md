# 股票多因子选股系统 📈

[![Python](https://img.shields.io/badge/python-3.8+-blue?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

> A股多因子选股系统 — 技术指标 + 资金流向 + 五行选股

## 功能模块

| 模块 | 文件 | 功能 |
|:----|:-----|:------|
| 📊 技术指标评分 | `technicals.py` | MACD/RSI/KDJ/布林带/量价/筹码/趋势 7大指标 |
| 🔬 多因子评分 | `multifactor.py` | 估值/成长/质量/动量/波动/资金/情绪/筹码/技术 9因子 |
| 🚀 选股引擎 | `china_stock_v4.py` | 新一代多因子选股+择时信号 |
| 📈 股票池缓存 | `stock_cache.py` | 多源数据缓存(Akshare/EastMoney) |
| 🖥️ 看盘仪表盘 | `dashboard.py` | 实时行情看板 |
| 🕐 午后精选 | `afternoon_picks.py` | 14:30尾盘选股 |

## 快速使用

```bash
python watch_stocks.py     # 监控中科仪+迅策
python afternoon_picks.py  # 午后尾盘选股
python dashboard.py        # 看盘仪表盘
```

## 技术栈

- **数据源**: akshare, eastmoney
- **技术分析**: ta-lib, numpy, pandas
- **可视化**: matplotlib, mplfinance
- **模型**: Elo评分, 多因子加权

---

## 📜 License

MIT © 2026
