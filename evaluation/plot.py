import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


class PerformancePlotter:

    def __init__(self):
        # 设置全局绘图风格
        sns.set_theme(style="whitegrid", palette="muted")
        # 解决中文字体显示问题 (若你的策略名叫中文)
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Arial', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

    def plot_metrics_dashboard(self, summary_records: list):
        """
        绘制多维度绩效对比仪表盘
        :param summary_records: 包含各个策略表现字典的列表 (来自 sandbox_test)
        """
        if not summary_records:
            print("❌ 没有数据可供绘制")
            return

        # 转换为 DataFrame 方便处理
        df = pd.DataFrame(summary_records)

        # 提取我们要画的 8 个核心指标的准确列名
        target_metrics = [
            "总收益率(%)", "年化收益率(%)", "最大回撤(%)",
            "夏普比率", "索提诺比率", "胜率(%)",
            "Profit Loss ratio", "总交易次数"
        ]

        # 过滤掉不在 dataframe 中的列
        plot_metrics = [m for m in target_metrics if m in df.columns]

        if "策略名称" not in df.columns:
            # 如果你的字典 key 是英文，使用英文映射
            target_metrics = [
                "Total Return (%)", "CAGR (%)", "Max Drawdown (%)",
                "Sharpe Ratio", "Sortino Ratio", "Win Rate (%)",
                "Profit Loss ratio", "Total Trades"
            ]
            plot_metrics = [m for m in target_metrics if m in df.columns]

        # 计算网格布局 (比如 8 个指标，就是 2 行 4 列)
        n_metrics = len(plot_metrics)
        cols = 4
        rows = (n_metrics + cols - 1) // cols

        # 创建一个巨大的画板
        fig, axes = plt.subplots(rows, cols, figsize=(20, 5 * rows))
        fig.suptitle('量化策略核心绩效对比仪表盘 (Strategy Performance Dashboard)', fontsize=22, fontweight='bold',
                     y=1.02)

        # 扁平化轴数组，方便遍历
        axes = axes.flatten()

        for i, metric in enumerate(plot_metrics):
            ax = axes[i]

            # 为不同维度的指标赋予不同的颜色渐变
            # 收益/胜率类用绿色系，回撤类用红色系，中性次数用蓝色系
            if "回撤" in metric or "Drawdown" in metric:
                palette = "Reds_r"
            elif "次数" in metric or "Trades" in metric:
                palette = "Blues"
            else:
                palette = "crest"  # 蓝绿渐变

            # 绘制柱状图
            sns.barplot(
                x="策略名称" if "策略名称" in df.columns else "Strategy",
                y=metric,
                data=df,
                ax=ax,
                palette=palette
            )

            ax.set_title(metric, fontsize=16, fontweight='bold', pad=15)
            ax.set_xlabel('')
            ax.set_ylabel('')

            # 倾斜 X 轴的策略名称，防止名字太长重叠
            ax.tick_params(axis='x', rotation=30)

            # 【黑科技】：在柱子顶部自动标注具体数值
            for p in ax.patches:
                height = p.get_height()
                # 如果是回撤（负数），字写在柱子下面；正数写在上面
                xytext = (0, 5) if height >= 0 else (0, -15)
                ax.annotate(
                    f'{height:.2f}' if "次数" not in metric and "Trades" not in metric else f'{int(height)}',
                    (p.get_x() + p.get_width() / 2., height),
                    ha='center', va='bottom' if height >= 0 else 'top',
                    xytext=xytext,
                    textcoords='offset points',
                    fontsize=12,
                    fontweight='bold'
                )

            # 增加水平 0 轴参考线
            ax.axhline(0, color='black', linewidth=1.2, alpha=0.5)

        # 隐藏多余的空白子图 (如果指标数不是 4 的倍数)
        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        # 调整布局间距
        plt.tight_layout()

        # 保存图片而不阻塞终端
        save_path = Path(__file__).resolve().parent.parent / "output" / "dashboard.png"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 仪表盘已成功保存至: {save_path}")

        # 仅在非服务器环境下展示
        try:
            plt.show(block=False)
            plt.pause(3)  # 弹窗展示 3 秒后自动关闭，程序继续运行
        except Exception:
            pass
