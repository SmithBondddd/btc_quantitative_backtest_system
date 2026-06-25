import numpy as np
import pandas as pd
from strategy.base import BaseStrategy

class DonchianTrendStrategy(BaseStrategy):
    """
    唐奇安通道趋势策略
    """
    def __init__(self):
        pass

    """
    多头趋势跟随策略
    """
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 获取上一根 K 线的通道极值
        prev_up_20 = df['DONCHIAN_UP_20'].shift(1)
        prev_dn_10 = df['DONCHIAN_DN_10'].shift(1)

        # 2. 布尔逻辑网
        # --- 多头逻辑 ---
        # 价格在 120 均线之上(牛市)，且突破 20 周期高点
        long_entry = (df['close'] > prev_up_20) & (df['close'] > df['EMA_120'])
        long_exit = (df['close'] < prev_dn_10)

        # 3. 极速状态机注入
        # --- 多头通道 ---
        df['long_pos'] = np.nan
        df.loc[long_entry, 'long_pos'] = 1
        df.loc[long_exit, 'long_pos'] = 0
        df['long_pos'] = df['long_pos'].ffill().fillna(0)

        # 4. 净头寸缝合
        df['position'] = df['long_pos']
        df.drop(columns=['long_pos'], inplace=True)

        return df
