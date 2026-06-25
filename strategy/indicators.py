import pandas as pd


class IndicatorsCalculator:
    def __init__(self,
                 ema_spans=(9, 20, 50, 120, 200),
                 macd_params=(12, 26, 9),
                 rsi_period=14,
                 atr_period=14,
                 boll_period=20, boll_std_multiplier=(1.0, 2.0, 3.0),
                 donchian_period=(10, 20)
                 ):
        """
        计算各个技术指标

        参数:
        - ema_spans: ema的统计周期
        - macd_params: macd的统计周期
        - rsi_period: rsi的统计周期
        - atr_period: atr的统计周期
        - boll_period: 布林带中轨的周期; boll_std_multiplier:布林带标准差乘数
        - donchian_period: 唐奇安通道周期

        返回:
        - 带有上述技术指标的DataFrame
        """

        self.ema_spans = ema_spans
        self.macd_fast, self.macd_slow, self.macd_signal = macd_params
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.boll_period = boll_period
        self.boll_std_multiplier = boll_std_multiplier
        self.donchian_period = donchian_period

    def indicators_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = self._ema_calculator(df)
        df = self._macd_calculator(df)
        df = self._rsi_calculator(df)
        df = self._atr_calculator(df)
        df = self._boll_calculator(df)
        df = self._vwap_calculator(df)
        df = self._donchian_calculator(df)
        df.dropna(inplace=True)

        return df

    def _ema_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        # EMA计算区域
        for span in self.ema_spans:
            df[f'EMA_{span}'] = df['close'].ewm(span=span, adjust=False).mean()

        return df

    def _macd_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        # MACD计算区域
        df['EMA_FAST'] = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        df['EMA_SLOW'] = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['MACD_DIF'] = df['EMA_FAST'] - df['EMA_SLOW']
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=self.macd_signal, adjust=False).mean()
        df['MACD_HIST'] = df['MACD_DIF'] - df['MACD_DEA']
        df.drop(columns=['EMA_FAST', 'EMA_SLOW'], inplace=True)

        return df

    def _rsi_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        period = self.rsi_period
        # 计算相邻两根 K 线收盘价的差值
        delta = df['close'].diff()
        # 求出上涨动能和下跌动能
        gain = delta.clip(lower=0)
        loss = delta.clip(upper=0).abs()

        # 计算 Wilder 改进版指数移动平均 (RMA/SMMA), 平滑常数是 alpha = 1/period
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

        # 注入 1e-10 (0.0000000001) 作为微小常数，防御除以 0 导致的 NaN / Inf 崩溃
        rs = avg_gain / (avg_loss + 1e-10)
        df[f'RSI_{period}'] = 100 - (100 / (1 + rs))

        return df

    def _atr_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        period = self.atr_period

        # 1. 向量化跨期对齐：获取上一根 K 线的收盘价
        prev_close = df['close'].shift(1)

        # 2. 计算 TR 的三个组成部分
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()

        # 3. 跨列求最大值：将三根柱子拼装在一起，横向取最大值
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 4. 计算 ATR (对 TR 进行 Wilder 改进版指数平滑)
        df[f'ATR_{period}'] = tr.ewm(alpha=1 / period, adjust=False).mean()

        return df

    def _boll_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        n = self.boll_period
        k_1, k_2, k_3 = self.boll_std_multiplier
        k1, k2, k3 = int(k_1), int(k_2), int(k_3)

        # 1. 计算核心基座：中轨 (SMA) 与 总体标准差 (ddof=0)
        df['BOLL_MB'] = df['close'].rolling(window=n).mean()
        std = df['close'].rolling(window=n).std(ddof=0)

        # 2. 向量化展开多重火力网 (极其廉价的矩阵加减法)
        # 内部震荡网 (k=1)
        df[f'BOLL_UP_{k1}'] = df['BOLL_MB'] + k_1 * std
        df[f'BOLL_DN_{k1}'] = df['BOLL_MB'] - k_1 * std

        # 标准回归网 (k=2)
        df[f'BOLL_UP_{k2}'] = df['BOLL_MB'] + k_2 * std
        df[f'BOLL_DN_{k2}'] = df['BOLL_MB'] - k_2 * std

        # 极端趋势/黑天鹅网 (k=3)
        df[f'BOLL_UP_{k3}'] = df['BOLL_MB'] + k_3 * std
        df[f'BOLL_DN_{k3}'] = df['BOLL_MB'] - k_3 * std

        return df

    def _vwap_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        # 1. 计算 Typical Price (典型价格) 与 微观成交额
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        pv = typical_price * df['volume']

        # ==========================================
        # 2. 日内锚定 (Daily Anchored VWAP)
        # ==========================================
        # df.index.date 生成绝对日期 (如 2024-06-15)
        cumulative_pv_day = pv.groupby(df.index.date).cumsum()
        cumulative_volume_day = df['volume'].groupby(df.index.date).cumsum()
        df['VWAP_DAILY'] = cumulative_pv_day / (cumulative_volume_day + 1e-10)

        # ==========================================
        # 3. 周内锚定 (Weekly Anchored VWAP)
        # ==========================================

        week_period = df.index.to_period('W')
        cumulative_pv_week = pv.groupby(week_period).cumsum()
        cumulative_volume_week = df['volume'].groupby(week_period).cumsum()
        df['VWAP_WEEKLY'] = cumulative_pv_week / (cumulative_volume_week + 1e-10)

        return df

    def _donchian_calculator(self, df: pd.DataFrame) -> pd.DataFrame:
        """全量唐奇安通道算子 (支持多空双向)"""
        short_period, long_period = self.donchian_period
        # 20周期极值 (进场线)
        df[f'DONCHIAN_UP_{long_period}'] = df['high'].rolling(window=long_period).max()

        # 10周期极值 (逃生线)
        df[f'DONCHIAN_DN_{short_period}'] = df['low'].rolling(window=short_period).min()
        return df

