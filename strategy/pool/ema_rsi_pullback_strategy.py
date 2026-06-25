import numpy as np
import pandas as pd
from strategy.base import BaseStrategy

class EmaRsiPullbackStrategy(BaseStrategy):
    """
    EMA_RIS回撤策略
    """

    def __init__(self):
        pass

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ==========================================
        # 1. 多头逻辑网 (极度降频 + 宏观防线)
        # ==========================================

        # 触发：绝对的多头趋势中，出现极其深度的极值砸盘
        long_entry = (
                (df['EMA_50'] > df['EMA_200']) &
                (df['close'] < df['EMA_50']) &
                (df['close'] > df['EMA_200']) &
                (df['RSI_14'] < 30)
        )

        # 退出：一旦价格实体跌穿了 EMA_200，说明牛市逻辑彻底崩塌，立刻无条件割肉。
        long_exit = (df['RSI_14'] > 75) | (df['close'] < df['EMA_200'])

        # ==========================================
        # 2. 单轨绝对状态机
        # ==========================================
        df['position'] = np.nan

        # 规则 1: 离场权限绝对优先 (保命第一)
        df.loc[long_exit, 'position'] = 0

        # 规则 2: 后处理入场指令
        df.loc[long_entry, 'position'] = 1

        # 状态顺延与纳秒级空值填充
        df['position'] = df['position'].ffill().fillna(0)

        # 输出纯净矩阵
        return df
