import numpy as np
import pandas as pd
from engine.risk import RiskModel


class VectorizedBacktestEngine:

    def __init__(self, initial_capital: float, leverage: float):
        self.initial_capital = initial_capital
        self.leverage = leverage

    def _align_and_route(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # 状态错位对齐，杜绝未来函数
        df['actual_pos'] = df['position'].shift(1).fillna(0)
        df['delta_pos'] = df['actual_pos'] - df['actual_pos'].shift(1).fillna(0)
        return df

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._align_and_route(df)

        # 1. 抓取开仓瞬间的价格作为绝对锚点
        entry_condition = (df['delta_pos'] != 0) & (df['actual_pos'] != 0)
        df['entry_price'] = np.where(entry_condition, df['close'].shift(1), np.nan)
        df['entry_price'] = df['entry_price'].ffill()

        # 2. 计算相对于开仓价的未实现盈亏百分比
        trade_pnl_pct = df['actual_pos'] * (df['close'] - df['entry_price']) / df['entry_price'] * self.leverage

        # 3. 高维等价转换：将线性盈亏逆向折算为可连乘的 K 线单步收益率
        # 获取上一根 K 线的盈亏状态 (如果发生换仓反手，则重置为 0)
        prev_trade_pnl_pct = np.where(
            df['actual_pos'] == df['actual_pos'].shift(1).fillna(0),
            trade_pnl_pct.shift(1).fillna(0),
            0.0
        )

        # r_t = (PnL_t - PnL_{t-1}) / (1 + PnL_{t-1})
        raw_step_return = (trade_pnl_pct - prev_trade_pnl_pct) / (1.0 + prev_trade_pnl_pct)
        # 防御极端情况下的除零或 NaN 污染
        raw_step_return = np.nan_to_num(raw_step_return, nan=0.0, posinf=0.0, neginf=0.0)

        # 获取近似动态资金规模
        rough_multiplier = np.clip(1.0 + raw_step_return, 0.0, np.inf)

        # 将 NumPy 数组重新包装为 Pandas Series，并缝合原时间索引
        rough_equity = pd.Series(self.initial_capital * rough_multiplier.cumprod(), index=df.index)

        # 使用预演资金池深度，估算当时的真实订单体积
        dynamic_equity = rough_equity.shift(1).fillna(self.initial_capital)
        dynamic_order_notional = dynamic_equity * self.leverage * np.abs(df['delta_pos'])
        dynamic_current_notional = dynamic_equity * self.leverage * np.abs(df['actual_pos'])

        # 施加真实物理法则 (摩擦与爆仓)
        # 1. 动态冲击滑点扣减 (基于真实的预演体积)
        friction_rate = RiskModel.calc_friction_cost_rate(
            order_notional=dynamic_order_notional.values,
            kline_quote_volume=df['quote_volume'].values,
            fee_rate=0.0004, base_slippage=0.0001, impact_factor=0.05
        )
        turnover = np.abs(df['delta_pos']) * self.leverage
        friction_pct = turnover * friction_rate

        # 👑 进阶物理法则：永续合约资金费率 (Funding Rate) 摩擦,如果未来 df 传入了真实的逐小时 funding_rate 列，就用真实的；否则用币安默认基准万分之一
        current_funding_rate = df.get('funding_rate', 0.0001)

        # 识别资金费率结算时刻 (币安结算为北京时间的 00:00, 08:00, 16:00)
        is_funding_time = df.index.hour.isin([0, 8, 16])

        # 费率损耗 = 是否结算时刻 * 仓位方向 * 费率 * 杠杆
        # 多单支付费率(损耗增加)，空单收取费率(负损耗=盈利)
        funding_friction_pct = np.where(
            is_funding_time,
            df['actual_pos'] * current_funding_rate * self.leverage,
            0.0
        )

        # 最终净单步收益率 = 裸收益率 - 开平仓滑点摩擦 - 持仓资金费率摩擦
        df['net_return'] = raw_step_return - friction_pct - funding_friction_pct
        net_step_return = df['net_return']

        # 2. 爆仓极值穿透判定 (引入逐仓杠杆红线)
        df['is_dead'] = RiskModel.check_liquidation(
            position=df['actual_pos'].values,
            entry_price=df['entry_price'].values,
            low_price=df['low'].values,
            high_price=df['high'].values,
            notional_value=dynamic_current_notional.values,
            leverage=self.leverage
        )

        # 3. 终极真实资金翻滚
        final_multiplier = np.clip(1.0 + net_step_return, 0.0, np.inf)
        # 一次爆仓，乘数归零，永远死亡
        final_multiplier = np.where(df['is_dead'], 0.0, final_multiplier)
        df['equity'] = self.initial_capital * final_multiplier.cumprod()

        # 辅助状态装填
        df['high_water_mark'] = df['equity'].cummax()
        df['drawdown'] = np.where(
            df['high_water_mark'] > 0,
            (df['equity'] - df['high_water_mark']) / df['high_water_mark'],
            0.0
        )

        # 只保留基础 K 线与引擎核心表现
        keep_cols = [
            'open', 'high', 'low', 'close',  # 基础 K 线数据 (timestamp 是索引，天然保留)
            'position',  # 策略生成的原始目标状态
            'actual_pos', 'delta_pos',  # 引擎处理后的实际持仓与换仓脉冲
            'net_return',  # 单步净收益率 (已扣除摩擦)
            'is_dead',  # 爆仓熔断脉冲
            'equity', 'high_water_mark', 'drawdown'  # 核心资金曲线三剑客: 净值, 净值最高点, 回撤
        ]


        return df[keep_cols]
