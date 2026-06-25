import numpy as np


class RiskModel:
    """
    纯静态风控计算引擎，无状态流转。
    [边界约定] 适用逐仓模式。
    """

    @staticmethod
    def calc_friction_cost_rate(
            order_notional: np.ndarray,
            kline_quote_volume: np.ndarray,
            fee_rate: float = 0.0004,
            base_slippage: float = 0.0001,
            impact_factor: float = 0.05
    ) -> np.ndarray:
        base_cost_rate = fee_rate + base_slippage

        # 增加对 np.isnan 的显式拦截，将极端无流动性或脏数据彻底隔离
        safe_volume = np.where((kline_quote_volume <= 0) | np.isnan(kline_quote_volume), 1e-10, kline_quote_volume)

        abs_notional = np.abs(order_notional)
        volume_ratio = abs_notional / safe_volume
        dynamic_slippage_rate = impact_factor * np.sqrt(volume_ratio)

        return base_cost_rate + dynamic_slippage_rate

    @staticmethod
    def check_liquidation(
            position: np.ndarray,
            entry_price: np.ndarray,
            low_price: np.ndarray,
            high_price: np.ndarray,
            notional_value: np.ndarray,
            leverage: float | np.ndarray
    ) -> np.ndarray:

        safe_entry = np.where(np.isnan(entry_price), np.inf, entry_price)

        mmr = np.select(
            [notional_value < 50000, notional_value < 250000, notional_value < 1000000],
            [0.004, 0.005, 0.010],
            default=0.025
        )

        liq_price_long = safe_entry * (1 - (1.0 / leverage) + mmr)
        liq_price_short = safe_entry * (1 + (1.0 / leverage) - mmr)

        is_long_dead = (position == 1) & (low_price <= liq_price_long)
        is_short_dead = (position == -1) & (high_price >= liq_price_short)

        return is_long_dead | is_short_dead