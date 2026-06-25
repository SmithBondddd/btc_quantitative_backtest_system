import warnings
import logging
import pandas as pd
from pathlib import Path

# 屏蔽第三方库的烦人警告
warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger('matplotlib.font_manager').disabled = True

# 导入所有自己手写的模块
from data.fetcher import DataFetcher
from strategy.indicators import IndicatorsCalculator

from strategy.pool.donchian_trend_strategy import DonchianTrendStrategy
from strategy.pool.ema_rsi_pullback_strategy import EmaRsiPullbackStrategy
from strategy.pool.triple_boll_strategy import TripleBollTrendStrategy


from engine.backtest import VectorizedBacktestEngine
from evaluation.metrics import PerformanceMetrics
from evaluation.plot import PerformancePlotter


class QuantSystem:
    """
    量化回测主系统类
    """

    def __init__(self, config: dict):
        self.config = config
        self.base_dir = Path(__file__).resolve().parent
        self.data_dir = self.base_dir / "data" / "history"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def run_pipeline(self, strategies: list):
        """
        执行主回测流水线
        """
        print(
            f"🚀 启动系统 | 品种: {self.config['symbol']} | 本金: {self.config['initial_capital']} U | 杠杆: {self.config['leverage']}x\n")

        # ==========================================
        # 1. [阶段一] 获取原始数据
        # ==========================================
        print("📥 [阶段一] 正在执行抓取程序...")
        fetcher = DataFetcher()
        raw_csv_path = fetcher.fetch_all_history(
            symbol=self.config['symbol'],
            timeframe=self.config['timeframe'],
            start_time_str=self.config['start_time'],
            save_dir=str(self.data_dir)
        )
        try:
            raw_df = pd.read_csv(raw_csv_path, index_col='timestamp', parse_dates=True)
        except FileNotFoundError:
            print(f"\n❌ 致命错误：找不到数据文件 {raw_csv_path}。")
            print("请检查网络代理是否畅通，或阶段一抓取是否被强制中断。")
            return

        # ==========================================
        # 2. [阶段二] 计算技术指标
        # ==========================================
        print("🏭 [阶段二] 正在计算技术指标矩阵...")
        calculator = IndicatorsCalculator()
        features_df = calculator.indicators_calculator(raw_df)

        summary_records = []

        # ==========================================
        # 3. [阶段三/四/五] 遍历测试外部传入的策略
        # ==========================================
        for strategy in strategies:
            strategy_name = strategy.get_strategy_name()
            print(f"\n⚙️ 正在测试策略: {strategy_name}")

            # 信号生成
            df_with_signal = strategy.generate_signals(features_df)

            # 物理撮合
            engine = VectorizedBacktestEngine(
                initial_capital=self.config['initial_capital'],
                leverage=self.config['leverage']
            )
            result_df = engine.run(df_with_signal)

            # 表现评估
            evaluator = PerformanceMetrics(df=result_df, initial_capital=self.config['initial_capital'])
            adv_metrics = evaluator.compute_metrics()

            # 收集画图和报表数据
            summary_records.append({
                "策略名称": strategy_name,
                "总收益率(%)": adv_metrics["Total Return (%)"],
                "年化收益率(%)": adv_metrics["CAGR (%)"],
                "最大回撤(%)": adv_metrics["Max Drawdown (%)"],
                "夏普比率": adv_metrics["Sharpe Ratio"],
                "索提诺比率": adv_metrics["Sortino Ratio"],
                "胜率(%)": adv_metrics["Win Rate (%)"],
                "盈亏比": adv_metrics["Profit Factor"],
                "总交易次数": adv_metrics["Total Trades"]
            })

        # ==========================================
        # 4. 打印报告与渲染图表
        # ==========================================
        summary_df = pd.DataFrame(summary_records)
        print("\n=======================================================================")
        print("🏆 终极表现汇总报告:")
        print("=======================================================================")
        print(summary_df.sort_values(by="总收益率(%)", ascending=False).to_string(index=False))
        print("=======================================================================\n")

        print("🎨 正在生成多面网格绩效仪表盘，请在弹出的窗口中查看...")
        plotter = PerformancePlotter()
        plotter.plot_metrics_dashboard(summary_records)


# ==============================================================================
# 🎯 用户操作区 (User Sandbox) - 使用者请看这里！
# ==============================================================================
if __name__ == "__main__":
    # 【1】修改全局回测参数
    USER_CONFIG = {
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "start_time": "1971-01-01 00:00:00",
        "initial_capital": 1000.0,
        "leverage": 1.0
    }
    """
    - "symbol" : 回测币种
    - "timeframe" : K线时间
    - "start_time" : 抓取数据的开始时间 (⚠️使用者请注意：开始时间默认设置是从第一笔订单开始抓取，如果修改抓取时间可能导致技术指标和binance平台对不上)
    - "initial_capital" : 初始资金
    - "leverage" : 杠杆倍率
    """

    # 【2】挑选你想回测的策略 (不想回测的直接用 # 注释掉或删除即可)
    ACTIVE_STRATEGIES = [
        DonchianTrendStrategy(),
        TripleBollTrendStrategy(),
        EmaRsiPullbackStrategy()
    ]

    # 【3】实例化系统并点火执行
    system = QuantSystem(config=USER_CONFIG)
    system.run_pipeline(strategies=ACTIVE_STRATEGIES)