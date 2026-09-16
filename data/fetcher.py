import ccxt
import pandas as pd
import datetime
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()


class DataFetcher:
    def __init__(self):
        # 动态读取代理配置
        http_proxy = os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('HTTPS_PROXY')

        proxies_config = {}
        if http_proxy and https_proxy:
            proxies_config = {
                'http': http_proxy,
                'https': https_proxy,
            }

        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True,
            'timeout': 30000,
            'proxies': proxies_config if proxies_config else None
        })

    def fetch_all_history(self, symbol: str, timeframe: str, start_time_str: str, save_dir: str = None) -> str:
        """
        带分页容错的全量历史 K 线抓取函数，数据自动增量合并并落地为 CSV
        """

        if save_dir is None:
            # 获取当前文件所在目录，并拼接出 history 文件夹路径
            current_dir = Path(__file__).resolve().parent
            save_dir_path = current_dir / "history"
        else:
            save_dir_path = Path(save_dir)

        # 确保物理目录树存在
        save_dir_path.mkdir(parents=True, exist_ok=True)

        # 规范化文件名并拼接完整落盘路径
        file_symbol = symbol.replace('/', '_')
        csv_path = save_dir_path / f"{file_symbol}_{timeframe}.csv"

        # 2. 时间解析与边界设定
        dt_obj = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        since_ms = int(dt_obj.timestamp() * 1000)
        now_ms = int(time.time() * 1000)

        # 判断是否有增量更新
        existing_df = None
        if csv_path.exists():
            print(f"🔍 侦测到本地历史数据: {csv_path}，启动断点续传协议...")
            # 加载历史数据，自动将时间列解析为 Pandas 内部的 DateTime 对象
            existing_df = pd.read_csv(csv_path, index_col='timestamp', parse_dates=True)

            if not existing_df.empty:
                # 提取最后一条记录的时间
                last_time_obj = existing_df.index[-1]

                # 逆向时空解析：北京时间 -> 赋予时区 -> 转为 UTC 毫秒时间戳
                target_timezone = 'Asia/Shanghai'
                last_saved_ms = int(last_time_obj.tz_localize(target_timezone).timestamp() * 1000)

                # 校验：如果本地数据的时间比配置的起点更靠后，强行推移起点！
                if last_saved_ms >= since_ms:
                    since_ms = last_saved_ms + 1
                    print(f"⏩ 触发增量更新！起点自动推进至本地最新时间: {last_time_obj} 之后")
        # ==========================================

        all_dfs = []
        batch_count = 0

        print(f"🚀 开始全量下载 {symbol} [{timeframe}] 永续合约历史数据...")
        print(f"起点: {start_time_str} -> 终点: 当前时间")

        # 3. 分页抓取主循环
        max_batches = 5000  # 约可抓取 500 万根 K 线，硬性熔断阈值
        while since_ms < now_ms:
            if batch_count >= max_batches:
                print("⚠️ 触发安全熔断：达到最大分页请求次数。")
                break
            try:
                # 将 "BTC/USDT" 转换为币安底层识别的 "BTCUSDT"
                binance_symbol = symbol.replace('/', '')
                # 绕过 CCXT 标准化，直接调用币安 U 本位合约底层 API，币安单次请求上限为 1000 根 K 线
                raw_ohlcv = self.exchange.fapiPublicGetKlines({
                    'symbol': binance_symbol,
                    'interval': timeframe,
                    'startTime': since_ms,
                    'limit': 1000
                })

                if not raw_ohlcv:
                    print("查无更多更近的历史数据，抓取循环正常结束。")
                    break

                # 将返回数据转为DataFrame
                df_batch = pd.DataFrame(raw_ohlcv, columns=[
                    'timestamp',               # 开盘时间
                    'open',                    # 开盘价
                    'high',                    # 最高价
                    'low',                     # 最低价
                    'close',                   # 收盘价
                    'volume',                  # 成交量
                    'close_time',              # K线收盘时间 (对量化作用不大，之后将其删除)
                    'quote_volume',            # 计价币种成交额
                    'count',                   # 交易笔数
                    'taker_buy_volume',        # 主动买入基础币种数量
                    'taker_buy_quote_volume',  # 主动买入计价币种金额
                    'ignore'                   # 币安预留字段(之后将其删除)
                ])

                df_batch.drop(columns=['close_time', 'ignore'], inplace=True)
                all_dfs.append(df_batch)

                # 提取当前批次最后一根 K 线的时间戳，转为纯数字
                last_ts = int(raw_ohlcv[-1][0])

                # 打印当前时间轴推进进度
                current_batch_time = datetime.datetime.fromtimestamp(last_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"✅ 已成功同步第 {batch_count + 1} 批次，数据推进至: {current_batch_time}")

                # 防死循环机制：下一次请求的起点为最后一根时间戳 + 1毫秒
                if last_ts <= since_ms:
                    break
                since_ms = last_ts + 1
                batch_count += 1

                # 根据 ccxt 内置权重延迟强制休眠
                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                # 生产级网络容错：遭遇网络抖动或代理断开时不崩溃，等待5秒后自动重试
                print(f"💥 抓取流遭遇偶发性异常: {e}，将在 5 秒后自动重试...")
                time.sleep(5)
                continue

        if not all_dfs:
            print("✅ 探测完毕：本地数据已是最新，无需向交易所发起增量请求。")
            return str(csv_path)

        # 4. 向量化矩阵合并与终极清洗 (Vectorized Post-Processing)
        print("📊 正在执行内存矩阵合并与标准时序清洗...")
        final_df = pd.concat(all_dfs, ignore_index=True)

        # ==========================================
        # 🚀 高阶类型安全：动态隔离时间戳，转换订单流矩阵
        # ==========================================
        # 动态提取除 timestamp 外的所有列（完美兼容 10 维、12 维等一切变体）
        numeric_cols = [col for col in final_df.columns if col != 'timestamp']
        final_df[numeric_cols] = final_df[numeric_cols].astype(float)

        # 将原始数据(int/str)直接转换为 Pandas DateTime 格式并设为行索引
        final_df['timestamp'] = final_df['timestamp'].astype('int64')
        final_df['timestamp'] = pd.to_datetime(final_df['timestamp'], unit='ms')
        final_df.set_index('timestamp', inplace=True)
        # ==========================================

        # --- 核心时区转换逻辑 (M4: 防重复时区转换崩溃) ---
        target_timezone = 'Asia/Shanghai'
        if final_df.index.tz is None:
            # 如果是无时区对象 (Naive)，先赋予 UTC 再转换
            final_df.index = final_df.index.tz_localize('UTC').tz_convert(target_timezone).tz_localize(None)
        else:
            # 如果已经是带时区对象 (Aware)，直接转换
            final_df.index = final_df.index.tz_convert(target_timezone).tz_localize(None)

        # 新老数据终极缝合
        if existing_df is not None and not existing_df.empty:
            print("🧲 正在将本次增量数据与本地历史数据进行无缝熔炼...")
            final_df = pd.concat([existing_df, final_df])

        # 剔除因分页交叉可能导致的极其微量的重复行
        final_df = final_df[~final_df.index.duplicated(keep='first')]
        # 确保整条时间轴绝对正序
        final_df.sort_index(ascending=True, inplace=True)
        # 删除未闭合K线，防止回测时引入“未来函数”偏差
        final_df = final_df.iloc[:-1]

        # 5. 落地存储
        final_df.to_csv(csv_path)
        print(f"📦 离线数据成功落地。路径: {csv_path}")
        print(f"总计样本量: {len(final_df)} 根 K 线。")
        return str(csv_path)

