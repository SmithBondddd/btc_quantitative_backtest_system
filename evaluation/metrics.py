import numpy as np
import pandas as pd


class PerformanceMetrics:
    """
    华尔街标准绩效评估器 (纯向量化实现)
    """

    def __init__(self, df: pd.DataFrame, initial_capital: float = 10000.0, rfr: float = 0.015, af: int = 8760):
        """
        初始化评估器
        - df: 回测引擎 (Phase 4) 输出的完整结果矩阵
        - initial_capital: 初始资金 (计算收益率用)
        - rfr: 年化无风险利率 (Risk-Free Rate)，默认 1.5%
        - af: 年化因子 (Annualization Factor)，1h级别K线af为 365 * 24 = 8760
        """
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.rfr = rfr
        self.af = af

    def compute_metrics(self) -> dict:
        """
        计算并返回所有核心表现指标的字典
        """
        # --- 基础收益体系 ---
        total_return = self._total_return()
        annualized_return = self._annualized_return()

        # --- 风险与性价比体系 ---
        max_drawdown = self._max_drawdown()
        sharpe = self._sharpe_ratio()
        sortino = self._sortino_ratio()

        # --- 微观交易统计 ---
        trade_stats = self._trade_statistics()

        # 组装输出报告
        metrics_report = {
            "Total Return (%)": total_return * 100,
            "CAGR (%)": annualized_return * 100,
            "Max Drawdown (%)": max_drawdown * 100,
            "Sharpe Ratio": sharpe,
            "Sortino Ratio": sortino,
            "Total Trades": trade_stats['total_trades'],
            "Win Rate (%)": trade_stats['win_rate'] * 100,
            "Profit Factor": trade_stats['profit_factor']
        }

        return metrics_report

    # ==========================================
    # 内部微观计算方法 (私有方法)
    # ==========================================

    def _total_return(self) -> float:
        # 计算总收益率
        final_equity = self.df['equity'].iloc[-1]
        return (final_equity - self.initial_capital) / self.initial_capital

    def _annualized_return(self) -> float:
        # 计算年化收益率
        total_days = (self.df.index[-1] - self.df.index[0]).days
        final_equity = self.df['equity'].iloc[-1]

        if total_days <= 0 or final_equity <= 0:
            return 0.0

        # 几何复利公式: (最终/初始) ^ (365 / 经历天数) - 1
        return (final_equity / self.initial_capital) ** (365.0 / total_days) - 1.0

    def _max_drawdown(self) -> float:
        # 计算最大回撤
        return self.df['drawdown'].min()

    def _sharpe_ratio(self) -> float:
        # 计算夏普比率
        net_return = self.df['net_return']

        # 物理对齐：把年化的无风险利率，降维摊平到每一小时
        hourly_rfr = self.rfr / self.af
        excess_return = net_return - hourly_rfr

        std = net_return.std()
        if std == 0 or np.isnan(std):
            return 0.0

        # 夏普公式：(超额收益均值 / 波动率) * 根号下年化因子
        return (excess_return.mean() / std) * np.sqrt(self.af)

    def _sortino_ratio(self) -> float:
        # 计算索提诺比率
        net_return = self.df['net_return']
        hourly_rfr = self.rfr / self.af
        excess_return = net_return - hourly_rfr

        # 仅截取亏损的 K 线来计算下行标准差 (Downside Deviation)
        downside_returns = net_return[net_return < 0]
        downside_std = downside_returns.std()

        if downside_std == 0 or np.isnan(downside_std):
            return 0.0

        return (excess_return.mean() / downside_std) * np.sqrt(self.af)

    def _trade_statistics(self) -> dict:
        # 交易统计
        df = self.df.copy()

        # 1. 计算每一根 K 线的绝对盈亏 (USDT)
        df['step_pnl'] = df['equity'].diff().fillna(0)

        # 2. 寻找开仓点
        is_new_trade = (df['delta_pos'] != 0) & (df['actual_pos'] != 0)

        # 3. 生成交易ID
        df['trade_id'] = is_new_trade.cumsum()

        # 4. 剔除开仓前的的区域
        valid_trades_df = df[df['trade_id'] > 0]

        if valid_trades_df.empty:
            return {'total_trades': 0, 'win_rate': 0.0, 'profit_factor': 0.0}

        # 5. 按照 trade_id 聚合，算出每一笔完整交易的最终盈亏
        trade_pnl = valid_trades_df.groupby('trade_id')['step_pnl'].sum()

        # 6. 计算终极交易统计指标
        total_trades = len(trade_pnl)
        winning_trades = (trade_pnl > 0).sum()

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        gross_profit = trade_pnl[trade_pnl > 0].sum()
        # 取绝对值防止除以负数
        gross_loss = np.abs(trade_pnl[trade_pnl < 0].sum())

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor
        }
