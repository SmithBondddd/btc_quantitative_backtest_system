import pandas as pd
import numpy as np
from strategy.base import BaseStrategy


class TripleBollTrendStrategy(BaseStrategy):
    """
    三重布林带趋势策略
    """

    def __init__(self):
        pass

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 提取前置判定基准线 (严格防止未来函数)
        prev_close = df['close'].shift(1)
        prev_up_2 = df['BOLL_UP_2'].shift(1)

        # ==========================================
        # 2. 纯多头逻辑网 (Long-Only 顺周期矩阵)
        # ==========================================

        # 触发：昨日在2倍上轨内，今日强势突破2倍上轨，且有大级别 VWAP 支撑
        long_entry = ((prev_close <= prev_up_2) &
                      (df['close'] > df['BOLL_UP_2']) &
                      (df['close'] > df['VWAP_WEEKLY']))

        # 撤退：跌破布林带中轨 (让利润充分奔跑)
        long_exit = (df['close'] < df['BOLL_MB'])


        # ==========================================
        # 3. 极简状态机 (拔除多空干涉)
        # ==========================================
        df['long_pos'] = np.nan
        df.loc[long_entry, 'long_pos'] = 1
        df.loc[long_exit, 'long_pos'] = 0
        df['long_pos'] = df['long_pos'].ffill().fillna(0)

        # 物理阉割空头：净头寸直接等同于多头头寸
        df['position'] = df['long_pos']

        # 矩阵物理清理：保持输出绝对纯净
        df.drop(columns=['long_pos'], inplace=True)

        return df
