from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """
    量化策略的绝对抽象基类。
    任何自定义策略必须继承此类，并严格遵守以下接口定义。
    """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        【强制契约】：信号生成器

        参数:
        df (pd.DataFrame): 阶段二产出的包含原始 K 线与所有技术指标的特征矩阵。

        返回:
        pd.DataFrame: 必须在原矩阵基础上新增一列 'position'。
                      'position' 的值域被严格锁定为 {1, 0, -1}。
                      绝对禁止在此处使用 for 循环。
        """
        pass

    def get_strategy_name(self) -> str:
        """
        【可选辅助】：获取当前策略名称，用于阶段五的表现评估日志与图表标题。
        默认返回类名。
        """
        return self.__class__.__name__