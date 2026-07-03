# 📊 股票量化分析工作台

一键启动的云端开发环境，内置 A股 + 港股多因子选股模型。

## 🚀 一键启动

1. 把这个文件夹推送到 GitHub
2. 在仓库页点 `Code` → `Codespaces` → `Create codespace on main`
3. 等 1 分钟自动装好环境

## 📂 文件结构

```
├── .devcontainer/
│   └── devcontainer.json    # Codespaces 配置 (自动安装所有依赖)
├── requirements.txt         # Python 包
├── china_stock_v3.py        # 多因子选股模型 (含操控检测)
├── afternoon_picks.py       # 每日14:30 尾盘选股
├── stock_cache.py           # SQLite 离线缓存引擎
├── watch_stocks.py          # 买入条件监控
├── demo.ipynb               # Jupyter 演示笔记本
└── README.md
```

## 💻 快速上手

```bash
# 1. 进入环境后, 终端已经装好所有依赖

# 2. 跑选股模型 (A股+港股)
python china_stock_v3.py --market all --top 20

# 3. 跑尾盘选股 (14:30专用)
python afternoon_picks.py

# 4. 监控买入条件
python watch_stocks.py

# 5. 启动 Jupyter 交互分析
jupyter notebook --port=8888
# Codespaces 会自动转发端口, 点提示打开

# 6. 或启动 Streamlit 看板
streamlit run dashboard.py
```

## 🔮 模型功能

- 9 大类因子, 40+ 细分因子
- 量化操控检测 (对倒/尾盘/量价背离)
- 热门概念评分 (AI/机器人/新能源等)
- 明日 10%+ 涨幅概率预测
- SQLite 离线缓存 (断网也能跑)

## 📝 配置

创建 `.env` 文件可配置：
```
# 如果要用 akshare (东方财富数据源), 不需要额外配置
# yfinance 是内置的, 也不需要配置
```
