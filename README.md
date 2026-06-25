<div align="center">

# 🚀 BTC 量化回测系统 <sub>BTC Quantitative Backtest System</sub>

[![Python](https://img.shields.io/badge/Python-≥3.10-blue?logo=python&logoColor=white)](https://www.python.org/)
[![pandas](https://img.shields.io/badge/pandas-≥2.0.0-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![NumPy](https://img.shields.io/badge/NumPy-≥1.24.0-013243?logo=numpy&logoColor=white)](https://numpy.org/)
[![CCXT](https://img.shields.io/badge/CCXT-≥4.0.0-black)](https://github.com/ccxt/ccxt)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-≥3.7.0-11557c?logo=python&logoColor=white)](https://matplotlib.org/)
[![Seaborn](https://img.shields.io/badge/Seaborn-≥0.12.0-79aab7)](https://seaborn.pydata.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

[中文说明](#-中文版)　|　[English](#-english-version)

</div>

---

# 🇨🇳 中文版

> [🔽 Jump to English Version](#-english-version)

---

## 📖 目录

- [项目简介](#项目简介)
- [架构设计](#架构设计)
- [数据流向图](#数据流向图)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [模块详解](#模块详解)
- [内置策略](#内置策略)
- [技术指标](#技术指标)
- [风控模型](#风控模型)
- [输出说明](#输出说明)
- [技术债与注意事项](#技术债与注意事项)
- [路线图](#路线图)

---

## 项目简介

**BTC 量化回测系统** 是一套面向加密货币永续合约的**纯向量化事件驱动回测引擎**。系统以 Binance USDⓈ-M 合约为数据源，通过四阶段流水线（数据拉取 → 指标计算 → 策略信号 → 物理撮合与评估），在数秒内完成数年历史行情的全量回测。

### 核心特性

- ⚡ **纯向量化计算** — 基于 Pandas/NumPy 矩阵运算
- 🛡️ **严格反未来函数** — 全链路 `.shift(1)` 延迟对齐，杜绝 Look-Ahead Bias
- 💰 **真实摩擦建模** — 手续费、动态滑点、订单冲击成本、逐仓强平判定
- 💸 **资金费率模拟** — 北京时间 00:00 / 08:00 / 16:00 结算，支持自定义费率序列
- 📡 **断点续传** — 增量拉取只下载新区间，自动与本地历史数据合并
- 📊 **多策略对比** — 一次运行产出所有策略的绩效仪表盘

---

## 架构设计

```
btc_quantitative_backtest_system/
│
├── .env.example             #   环境变量模板（纯净版，可安全上传）
├── .gitignore               #   Git 黑名单（拦截敏感凭据与运行时产物）
├── README.md                #   项目文档（中英双版）
├── requirements.txt         #   依赖清单（含最低版本约束）
├── main.py                  # 🎯 总控台：组装流水线，用户唯一需要交互的入口
│
├── data/                    # ── 阶段一：数据管道 ──
│   ├── fetcher.py           #   CCXT 数据拉取机（分页/容错/断点续传）
│   └── history/             #   K线本地沉淀池（CSV 被 .gitignore 排除）
│       └── .gitkeep         #   目录占位
│
├── strategy/                # ── 阶段二 & 三：特征与信号 ──
│   ├── __init__.py
│   ├── base.py              #   策略抽象基类（强制契约接口）
│   ├── indicators.py        #   技术指标计算器（EMA/MACD/RSI/ATR/BOLL/VWAP/Donchian）
│   └── pool/                #   策略池
│       ├── __init__.py
│       ├── donchian_trend_strategy.py     # 唐奇安非对称突破趋势
│       ├── ema_rsi_pullback_strategy.py   # 三重滤网顺势回踩
│       └── triple_boll_strategy.py        # 三重布林带极值冲浪
│
├── engine/                  # ── 阶段四：撮合与风控 ──
│   ├── backtest.py          #   向量化回测引擎（虚拟撮合/资金翻滚）
│   └── risk.py              #   风控计算器（滑点/强平/MMR阶梯）
│
├── evaluation/              # ── 阶段五：绩效评估 ──
│   ├── metrics.py           #   绩效指标（夏普/索提诺/最大回撤/盈亏比）
│   └── plot.py              #   可视化仪表盘（多策略对比柱状图）
│
└── output/                  #   图表输出目录
    └── .gitkeep             #   目录占位
```

---

## 数据流向图

```
                     ┌──────────────────────────────────────────────────────────────┐
                     │                    BTC 量化回测流水线                           │
                     └──────────────────────────────────────────────────────────────┘

  ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
  │          │     │              │     │              │     │                 │
  │ Binance  │────▶│ DataFetcher  │────▶│  Indicators  │────▶│   Strategies    │
  │ USDⓈ-M   │     │ (fetch_all)  │     │  Calculator  │     │  (3 strategies) │
  │   API    │     │              │     │              │     │                 │
  │          │     │  • 分页抓取   │     │ EMA MACD RSI │     │  • 信号生成      │
  │          │     │  • 断点续传   │     │ ATR BOLL VWAP│     │  • 状态机注入    │
  │          │     │  • 增量合并   │     │ Donchian     │     │  • position列    │
  └──────────┘     └──────┬───────┘     └──────┬───────┘     └───────┬─────────┘
                          │                    │                     │
                          ▼                    ▼                     ▼
                    data/history/         features_df           df + position
                    BTC_USDT_1h.csv      (带全部指标)            (带信号列)
                                                                      │
                          ┌───────────────────────────────────────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │                     │
               │ VectorizedBacktest  │
               │      Engine         │
               │                     │
               │  • position.shift   │  ◀── 防未来函数
               │  • 开仓价锚定       │
               │  • 杠杆PnL计算      │
               │  • 滑点摩擦扣减     │
               │  • 资金费率扣减     │
               │  • MMR强平判定      │
               │  • 资金曲线翻滚     │
               │                     │
               └─────────┬───────────┘
                         │
                         ▼
               ┌─────────────────────┐     ┌──────────────────────┐
               │                     │     │                      │
               │  PerformanceMetrics │────▶│  PerformancePlotter  │
               │                     │     │                      │
               │  • 总收益率/CAGR     │     │  • 多策略柱状对比       │
               │  • 夏普/索提诺       │      │  • 8维绩效仪表盘       │
               │  • 最大回撤          │     │  • 自动保存PNG           │
               │  • 胜率/盈亏比       │     │                         │
               └─────────────────────┘     └──────────────────────┘
```

---

## 快速开始

### 环境要求

| 依赖 | 最低版本 |
|------|----------|
| Python | 3.10+ |
| pandas | 2.0.0 |
| numpy | 1.24.0 |
| ccxt | 4.0.0 |
| python-dotenv | 1.0.0 |
| matplotlib | 3.7.0 |
| seaborn | 0.12.0 |

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/SmithBondddd/btc_quantitative_backtest_system.git
cd btc_quantitative_backtest_system

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量（可选）
# 编辑 .env 文件，设置代理（国内用户）或留空（海外服务器）
```

### 运行

```bash
python main.py
```

程序将自动：
1. 从 Binance 拉取 BTC/USDT 永续合约全量历史数据（仅首次，后续增量更新）
2. 计算全部技术指标
3. 遍历三个内置策略依次回测
4. 打印绩效汇总表并弹出对比仪表盘

---

## 配置说明

所有用户可配置项集中在 `main.py` 底部的 `USER_CONFIG` 字典：

```python
USER_CONFIG = {
    "symbol": "BTC/USDT",               # 交易对
    "timeframe": "1h",                  # K线周期（1m/5m/15m/1h/4h/1d...）
    "start_time": "1971-01-01 00:00:00",# 数据起点（设远古时间=从第一笔开始）
    "initial_capital": 1000.0,          # 初始本金 (USDT)
    "leverage": 1.0                     # 杠杆倍数
}
```

### 选择策略

在 `ACTIVE_STRATEGIES` 列表中注释/取消注释即可：

```python
ACTIVE_STRATEGIES = [
    DonchianTrendStrategy(),
    TripleBollTrendStrategy(),
    # EmaRsiPullbackStrategy(),  # 暂时禁用
]
```

### 代理配置

编辑 `.env` 文件（国内网络环境需配置）：

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

海外服务器留空即可自动跳过代理。

---

## 模块详解

### 1. 数据管道 — `data/fetcher.py`

| 功能 | 实现 |
|------|------|
| 数据源 | Binance USDⓈ-M 永续合约（通过 CCXT） |
| 分页 | 每批 1000 根 K 线，自动翻页 |
| 容错 | 网络异常等待 5 秒自动重试 |
| 断点续传 | 检测本地最新时间戳，仅拉取增量 |
| 时区 | Binance UTC → 北京时间 (Asia/Shanghai) |
| 清洗 | 去重、正序排列、剔除未闭合 K 线 |
| 熔断 | 最大 5000 批次（500 万根 K 线）硬性上限 |

### 2. 指标计算器 — `strategy/indicators.py`

计算 7 类技术指标，全部纯向量化实现：

| 指标族 | 列名 | 参数（可自定义） |
|--------|------|------------------|
| EMA | `EMA_9` `EMA_20` `EMA_50` `EMA_120` `EMA_200` | spans=(9,20,50,120,200) |
| MACD | `MACD_DIF` `MACD_DEA` `MACD_HIST` | (12,26,9) |
| RSI | `RSI_14` | period=14 |
| ATR | `ATR_14` | period=14 |
| 布林带 | `BOLL_MB` `BOLL_UP_1/2/3` `BOLL_DN_1/2/3` | period=20, k=(1.0,2.0,3.0) |
| VWAP | `VWAP_DAILY` `VWAP_WEEKLY` | 日内锚定 + 周内锚定 |
| Donchian | `DONCHIAN_UP_20` `DONCHIAN_DN_10` | (10,20) |

> ⚠️ **注意：** 布林带列名使用 `int()` 转换标准差乘数命名（1,2,3）。若需自定义非整数乘数，请注意列名冲突。当前策略均依赖默认乘数值。

### 3. 策略基类 — `strategy/base.py`

所有策略必须继承 `BaseStrategy` 并实现：

```python
@abstractmethod
def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    返回须在 df 中新增 'position' 列
    值域: {1 (做多), 0 (空仓), -1 (做空)}
    严禁使用 for 循环
    """
```

### 4. 回测引擎 — `engine/backtest.py`

核心撮合逻辑：

1. **信号对齐** — `position.shift(1)` 将信号延迟一根 K 线执行
2. **开仓价锚定** — 开仓瞬间以 `close.shift(1)` 锁定入场价
3. **杠杆 PnL** — `actual_pos × (close - entry) / entry × leverage`
4. **摩擦扣减** — 手续费 4bps + 基础滑点 1bps + 动态冲击成本
5. **资金费率** — 北京时间 00/08/16 时结算，默认万分之一
6. **强平判定** — 基于 Binance 逐仓 MMR 阶梯的精确强平价计算
7. **资金翻滚** — 净值 = 初始资金 × ∏(1 + 净单步收益率)

### 5. 风控模型 — `engine/risk.py`

| 功能 | 方法 |
|------|------|
| 摩擦成本率 | `calc_friction_cost_rate()` — 基础费率 + √(订单量/市场量) 冲击模型 |
| 强平判定 | `check_liquidation()` — 基于 MMR 阶梯和杠杆的精确强平价 |

MMR 阶梯（Binance BTCUSDT 逐仓）：

| 名义价值 (USDT) | MMR |
|-----------------|-----|
| < 50,000 | 0.4% |
| < 250,000 | 0.5% |
| < 1,000,000 | 1.0% |
| ≥ 1,000,000 | 2.5% |

> ⚠️ MMR 阶梯为硬编码，交易所调整参数时需手动同步。

### 6. 绩效评估 — `evaluation/metrics.py`

| 指标 | 公式 |
|------|------|
| 总收益率 | (最终净值 - 初始资金) / 初始资金 |
| 年化收益率 (CAGR) | (最终/初始)^(365/天) - 1 |
| 最大回撤 | min(净值/历史最高 - 1) |
| 夏普比率 | (超额收益均值 / 波动率) × √年化因子 |
| 索提诺比率 | (超额收益均值 / 下行波动率) × √年化因子 |
| 胜率 | 盈利交易数 / 总交易数 |
| 盈亏比 | 总盈利 / \|总亏损\| |

### 7. 可视化 — `evaluation/plot.py`

- 多策略 8 维绩效柱状对比图
- 自动保存至 `output/dashboard.png`
- 弹窗展示 3 秒后自动关闭（无 GUI 环境静默跳过）

---

## 内置策略

### 策略 1: 唐奇安非对称突破趋势

```
入场: close > DONCHIAN_UP_20(前值) AND close > EMA_120
离场: close < DONCHIAN_DN_10(前值)
方向: 仅做多
```

### 策略 2: 三重滤网顺势回踩

```
入场: EMA_50 > EMA_200          (第一重滤网：宏观趋势)
      AND close < EMA_50         (第二重滤网：回踩确认)
      AND close > EMA_200        (第二重滤网：支撑有效)
      AND RSI_14 < 30            (第三重滤网：超卖极值)
离场: RSI_14 > 75 OR close < EMA_200
方向: 仅做多
```

### 策略 3: 三重布林带极值冲浪

```
入场: prev_close ≤ BOLL_UP_2(前值)   (昨收在2σ上轨内)
      AND close > BOLL_UP_2           (今日强势突破2σ)
      AND close > VWAP_WEEKLY         (周 VWAP 支撑确认)
离场: close < BOLL_MB                 (回归中轨)
方向: 仅做多
```

---

## 技术债与注意事项

以下是已知的技术局限性，择期在后续版本中解决：

| 条目 | 说明 | 优先级 |
|------|------|--------|
| 单一交易所 | 仅支持 Binance USDⓈ-M，扩展需改造 DataFetcher | 中 |
| 仅做多 | 三个策略均无做空逻辑，熊市表现受限 | 中 |
| 无仓位管理 | 始终 100% 资金建仓，无凯利/固定分数/ATR 自适应 | 中 |
| MMR 阶梯硬编码 | 交易所参数变更需手动同步 `engine/risk.py` | 低 |
| 布林带列名约束 | `int()` 转换要求乘数为整数（默认 1.0/2.0/3.0 无影响） | 低 |

---

## 路线图

- **V2.0** — 做空策略支持 / 多交易所适配 / 仓位管理模块
- **V3.0** — Walk-Forward 推进优化 / 参数网格搜索 / 样本外测试
- **V4.0** — 多币种并发回测 / 投资组合优化 / 实盘信号桥接

---
## 📮联系作者：l1906249488@gmail.com

---

# 🇬🇧 English Version

> [🔙 Back to Chinese Version](#-中文版)

---

## 📖 Table of Contents

- [Introduction](#introduction)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Module Details](#module-details)
- [Built-in Strategies](#built-in-strategies)
- [Technical Indicators](#technical-indicators)
- [Risk Model](#risk-model)
- [Output](#output)
- [Technical Debt & Caveats](#technical-debt--caveats)
- [Roadmap](#roadmap)

---

## Introduction

**BTC Quantitative Backtest System** is a fully vectorized, event-driven backtesting engine for cryptocurrency perpetual futures. Using Binance USDⓈ-M futures as the data source, it executes a four-stage pipeline (Data Fetching → Indicator Calculation → Signal Generation → Physical Simulation & Evaluation) to backtest years of historical data in seconds.

### Key Features

- ⚡ **Pure Vectorized Computation** — Zero Python `for` loops; NumPy/Pandas matrix ops deliver millisecond-level execution
- 🛡️ **Look-Ahead Bias Prevention** — Full-chain `.shift(1)` alignment ensures no future information leakage
- 💰 **Realistic Friction Modeling** — Trading fees, dynamic slippage, order impact cost, isolated-margin liquidation
- 💸 **Funding Rate Simulation** — Settles at 00:00 / 08:00 / 16:00 Beijing time with configurable rate series
- 📡 **Resumable Downloads** — Incremental fetching with automatic local data merging
- 📊 **Multi-Strategy Comparison** — Single run produces a comparative performance dashboard for all active strategies

---

## Architecture

```
btc_quantitative_backtest_system/
│
├── .env.example             #   Env template (clean, safe to commit)
├── .gitignore               #   Git ignore rules (secrets & runtime artifacts excluded)
├── README.md                #   Project documentation (CN + EN)
├── requirements.txt         #   Dependency list (with minimum version constraints)
├── main.py                  # 🎯 Entry Point: pipeline orchestrator
│
├── data/                    # ── Stage 1: Data Pipeline ──
│   ├── fetcher.py           #   CCXT data fetcher (pagination/fault-tolerance/resume)
│   └── history/             #   Local OHLCV storage (CSV files excluded by .gitignore)
│       └── .gitkeep         #   Placeholder (preserves empty directory)
│
├── strategy/                # ── Stage 2 & 3: Features & Signals ──
│   ├── __init__.py
│   ├── base.py              #   Abstract strategy base (enforced interface contract)
│   ├── indicators.py        #   Technical indicator calculator (EMA/MACD/RSI/ATR/BOLL/VWAP/Donchian)
│   └── pool/                #   Strategy pool
│       ├── __init__.py
│       ├── donchian_trend_strategy.py     # Donchian Asymmetric Breakout Trend
│       ├── ema_rsi_pullback_strategy.py   # Triple Screen Pullback
│       └── triple_boll_strategy.py        # Triple Bollinger Band Surfing
│
├── engine/                  # ── Stage 4: Execution & Risk ──
│   ├── backtest.py          #   Vectorized backtest engine (virtual matching/equity compounding)
│   └── risk.py              #   Risk calculator (slippage/liquidation/MMR tiers)
│
├── evaluation/              # ── Stage 5: Performance ──
│   ├── metrics.py           #   Metrics (Sharpe/Sortino/Max Drawdown/Profit Factor)
│   └── plot.py              #   Dashboard (multi-strategy bar chart comparison)
│
└── output/                  #   Generated charts (PNG/CSV excluded by .gitignore)
    └── .gitkeep             #   Placeholder
```

---

## Data Flow

```
  ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
  │          │     │              │     │              │     │                 │
  │ Binance  │────▶│ DataFetcher  │────▶│  Indicators  │────▶│   Strategies    │
  │ USDⓈ-M   │     │ (fetch_all)  │     │  Calculator  │     │  (3 strategies) │
  │   API    │     │              │     │              │     │                 │
  └──────────┘     └──────┬───────┘     └──────┬───────┘     └───────┬─────────┘
                          │                    │                     │
                          ▼                    ▼                     ▼
                    data/history/         features_df           df + position
                    BTC_USDT_1h.csv      (all indicators)       (signal column)
                                                                      │
                          ┌───────────────────────────────────────────┘
                          ▼
               ┌─────────────────────┐
               │ VectorizedBacktest  │
               │      Engine         │
               │                     │
               │  • position.shift   │  ◀── anti-look-ahead bias
               │  • entry anchoring  │
               │  • leveraged PnL    │
               │  • slippage + fees  │
               │  • funding rate     │
               │  • MMR liquidation  │
               │  • equity compounding│
               └─────────┬───────────┘
                         ▼
               ┌─────────────────────┐     ┌──────────────────────┐
               │ PerformanceMetrics  │────▶│ PerformancePlotter   │
               │                     │     │                      │
               │  • Total Return/CAGR│     │  • Strategy comparison│
               │  • Sharpe/Sortino  │     │  • 8-dim dashboard   │
               │  • Max Drawdown    │     │  • Auto-save PNG     │
               │  • Win Rate/PF     │     │                      │
               └─────────────────────┘     └──────────────────────┘
```

---

## Quick Start

### Requirements

| Dependency | Minimum Version |
|------------|-----------------|
| Python | 3.10+ |
| pandas | 2.0.0 |
| numpy | 1.24.0 |
| ccxt | 4.0.0 |
| python-dotenv | 1.0.0 |
| matplotlib | 3.7.0 |
| seaborn | 0.12.0 |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/SmithBondddd/btc_quantitative_backtest_system.git
cd btc_quantitative_backtest_system

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables (optional)
# Edit .env to set proxy (users in mainland China) or leave blank (overseas servers)
```

### Running

```bash
python main.py
```

The program will automatically:
1. Fetch full BTC/USDT perpetual futures history from Binance (full download on first run, incremental thereafter)
2. Compute all technical indicators
3. Backtest all three built-in strategies sequentially
4. Print a performance summary table and display a comparison dashboard

---

## Configuration

All user-configurable parameters are centralized in `USER_CONFIG` at the bottom of `main.py`:

```python
USER_CONFIG = {
    "symbol": "BTC/USDT",               # Trading pair
    "timeframe": "1h",                  # Candle interval (1m/5m/15m/1h/4h/1d...)
    "start_time": "1971-01-01 00:00:00",# Data start (set ancient date = from first trade)
    "initial_capital": 1000.0,          # Initial capital (USDT)
    "leverage": 1.0                     # Leverage multiplier
}
```

### Strategy Selection

Enable or disable strategies in the `ACTIVE_STRATEGIES` list:

```python
ACTIVE_STRATEGIES = [
    DonchianTrendStrategy(),
    TripleBollTrendStrategy(),
    # EmaRsiPullbackStrategy(),  # Disabled
]
```

### Proxy Configuration

Edit `.env` (required for users in mainland China):

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

Leave blank if deploying on an overseas server — proxy will be skipped automatically.

---

## Module Details

### 1. Data Pipeline — `data/fetcher.py`

| Feature | Implementation |
|---------|---------------|
| Source | Binance USDⓈ-M perpetual futures (via CCXT) |
| Pagination | 1,000 candles per batch, automatic page turning |
| Fault Tolerance | Auto-retry after 5-second wait on network errors |
| Resumption | Detects latest local timestamp, fetches only new data |
| Timezone | Binance UTC → Beijing Time (Asia/Shanghai) |
| Cleaning | Dedup, chronological sort, remove unclosed candle |
| Safety Fuse | Hard cap at 5,000 batches (5 million candles) |

### 2. Indicator Calculator — `strategy/indicators.py`

Computes 7 indicator families, all fully vectorized:

| Family | Columns | Parameters (customizable) |
|--------|---------|---------------------------|
| EMA | `EMA_9` `EMA_20` `EMA_50` `EMA_120` `EMA_200` | spans=(9,20,50,120,200) |
| MACD | `MACD_DIF` `MACD_DEA` `MACD_HIST` | (12,26,9) |
| RSI | `RSI_14` | period=14 |
| ATR | `ATR_14` | period=14 |
| Bollinger | `BOLL_MB` `BOLL_UP_1/2/3` `BOLL_DN_1/2/3` | period=20, k=(1.0,2.0,3.0) |
| VWAP | `VWAP_DAILY` `VWAP_WEEKLY` | Daily-anchored + Weekly-anchored |
| Donchian | `DONCHIAN_UP_20` `DONCHIAN_DN_10` | (10,20) |

> ⚠️ **Note:** Bollinger Band column names use `int()` conversion on the standard deviation multipliers (1, 2, 3). If custom non-integer multipliers are used, be aware of potential column name collisions. All current strategies depend on the default integer multipliers.

### 3. Strategy Base — `strategy/base.py`

All strategies must inherit `BaseStrategy` and implement:

```python
@abstractmethod
def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Must append a 'position' column to df
    Value domain: {1 (long), 0 (flat), -1 (short)}
    Forbidden: Python for-loops
    """
```

### 4. Backtest Engine — `engine/backtest.py`

Core matching logic:

1. **Signal Alignment** — `position.shift(1)` delays execution by one candle
2. **Entry Anchoring** — Locks entry price at `close.shift(1)` on position open
3. **Leveraged PnL** — `actual_pos × (close - entry) / entry × leverage`
4. **Friction Deduction** — Fee 4bps + base slippage 1bps + dynamic impact cost
5. **Funding Rate** — Settled at Beijing 00:00 / 08:00 / 16:00, default 1bp
6. **Liquidation Check** — Precise liquidation price based on Binance isolated-margin MMR tiers
7. **Equity Compounding** — NAV = initial_capital × ∏(1 + net_step_return)

### 5. Risk Model — `engine/risk.py`

| Function | Method |
|----------|--------|
| Friction Cost Rate | `calc_friction_cost_rate()` — base rate + √(order_size / market_volume) impact model |
| Liquidation Check | `check_liquidation()` — precise liquidation price per MMR tier and leverage |

MMR Tiers (Binance BTCUSDT Isolated Margin):

| Notional Value (USDT) | MMR |
|-----------------------|-----|
| < 50,000 | 0.4% |
| < 250,000 | 0.5% |
| < 1,000,000 | 1.0% |
| ≥ 1,000,000 | 2.5% |

> ⚠️ MMR tiers are hardcoded. Manual sync required when the exchange updates parameters.

### 6. Performance Metrics — `evaluation/metrics.py`

| Metric | Formula |
|--------|---------|
| Total Return | (final_equity - initial) / initial |
| CAGR | (final/initial)^(365/days) - 1 |
| Max Drawdown | min(equity / running_max - 1) |
| Sharpe Ratio | (mean_excess_return / σ) × √annualization_factor |
| Sortino Ratio | (mean_excess_return / downside_σ) × √annualization_factor |
| Win Rate | winning_trades / total_trades |
| Profit Factor | gross_profit / |gross_loss| |

### 7. Visualization — `evaluation/plot.py`

- Multi-strategy 8-dimension bar chart comparison
- Auto-saved to `output/dashboard.png`
- Pop-up window auto-closes after 3 seconds (silently skipped in headless environments)

---

## Built-in Strategies

### Strategy 1: Donchian Asymmetric Breakout Trend

```
Entry:  close > DONCHIAN_UP_20(prev) AND close > EMA_120
Exit:   close < DONCHIAN_DN_10(prev)
Direction: Long only
```

### Strategy 2: Triple Screen Pullback

```
Entry:  EMA_50 > EMA_200              (Screen 1: macro trend)
        AND close < EMA_50            (Screen 2: pullback)
        AND close > EMA_200           (Screen 2: support intact)
        AND RSI_14 < 30               (Screen 3: oversold extreme)
Exit:   RSI_14 > 75 OR close < EMA_200
Direction: Long only
```

### Strategy 3: Triple Bollinger Band Surfing

```
Entry:  prev_close ≤ BOLL_UP_2(prev)  (yesterday within 2σ band)
        AND close > BOLL_UP_2          (today breaks above 2σ)
        AND close > VWAP_WEEKLY        (weekly VWAP support)
Exit:   close < BOLL_MB               (returns to midline)
Direction: Long only
```

---

## Technical Debt & Caveats

Known limitations to be addressed in future versions:

| Item | Description | Priority |
|------|-------------|----------|
| Single Exchange | Binance USDⓈ-M only; extending requires DataFetcher refactor | Medium |
| Long-Only | All three strategies lack short logic; limited in bear markets | Medium |
| No Position Sizing | Always 100% capital per trade; no Kelly / fixed-fractional / ATR-adaptive sizing | Medium |
| Hardcoded MMR Tiers | Exchange parameter changes require manual sync to `engine/risk.py` | Low |
| BOLL Column Name Constraint | `int()` conversion requires integer multipliers (default 1.0/2.0/3.0 unaffected) | Low |

---

## Roadmap

- **V2.0** — Short strategy support / Multi-exchange adapter / Position sizing module
- **V3.0** — Walk-Forward optimization / Parameter grid search / Out-of-sample testing
- **V4.0** — Multi-asset concurrent backtesting / Portfolio optimization / Live signal bridge

---
📮Email：l1906249488@gmail.com
---

<div align="center">

[🔝 Back to Top](#-btc-量化回测系统-)

</div>
