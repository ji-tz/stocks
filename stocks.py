"""后端业务模块：提供数据导入与策略运行的纯函数接口。

职责：
 - 将与具体业务相关的功能集中到本模块（供测试直接调用）
 - 提供 `init()`、`get_data()`、`run_mean_cost()`、`run_sma_backtest()` 等接口

本模块不启动 Web 服务，仅包含可被 `gui/web.py` 和 `main.py` 调用的函数。
"""
import os
import traceback
import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, Mapping

from source.data_provider import get_data as _get_data

try:
    from simulator.simulator import simulate_mean_cost, simulate_fixed_amount
except Exception as _e:
    # 兼容性：若 simulator 不可用，保留 None
    import warnings
    warnings.warn(f"simulator 模块不可用，相关功能将被禁用: {_e}", ImportWarning, stacklevel=2)
    simulate_mean_cost = None
    simulate_fixed_amount = None


TRADE_PRICE_OPEN = 'open'
SUPPORTED_TRADE_PRICE_FIELDS = ('open', 'close', 'high', 'low')


@dataclass(frozen=True)
class StrategyParameter:
    """策略参数定义。"""

    name: str
    label: str
    caster: Callable[[Any], Any]
    default: Any
    description: str = ''
    required: bool = False

    def parse(self, raw_value: Any) -> Any:
        """将表单或外部输入转换为策略内部参数。"""
        if raw_value is None or raw_value == '':
            if self.required and self.default is None:
                raise ValueError(f"策略参数 {self.name} 不能为空")
            return self.default
        return self.caster(raw_value)


@dataclass(frozen=True)
class StrategySpec:
    """策略规格定义。"""

    key: str
    label: str
    runner: Callable[..., Dict[str, Any]]
    parameters: tuple[StrategyParameter, ...] = ()
    description: str = ''
    supported_trade_prices: tuple[str, ...] = (TRADE_PRICE_OPEN,)


@dataclass
class BacktestRequest:
    """统一的回测请求。"""

    symbol: str = '600900'
    strategy: str = 'sma'
    source: object = 'auto'
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    lot_size: float = 100.0
    init_cash: float = 100000.0
    trade_price: str = TRADE_PRICE_OPEN
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    progress_callback: Optional[Callable[[int, int], None]] = None


def _validate_date_str(value: Optional[str]) -> Optional[str]:
    """校验并保留支持的日期格式。"""
    if value is None:
        return None
    value = str(value).strip()
    if value == '':
        return None
    import re
    if re.fullmatch(r"\d{8}", value):
        return value
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    raise ValueError(f"不支持的日期格式: {value}. 请使用 YYYYMMDD 或 YYYY-MM-DD")


def _normalize_for_source(value: Optional[str], source: object) -> Optional[str]:
    """按数据源需要规范日期。"""
    if value is None:
        return None

    source_lower = ''
    if isinstance(source, str):
        source_lower = source.lower()

    if '-' not in value and len(value) == 8:
        return value
    if source_lower == 'baostock':
        return value
    return value.replace('-', '')


def _normalize_strategy_params(spec: StrategySpec, strategy_params: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """按策略规格规范化参数。"""
    params = dict(strategy_params or {})
    normalized: Dict[str, Any] = {}

    allowed_names = {parameter.name for parameter in spec.parameters}
    unknown_names = sorted(set(params.keys()) - allowed_names)
    if unknown_names:
        raise ValueError(f"策略 {spec.key} 不支持参数: {', '.join(unknown_names)}")

    for parameter in spec.parameters:
        normalized[parameter.name] = parameter.parse(params.get(parameter.name))

    return normalized


def _discover_auto_strategy_specs() -> Dict[str, StrategySpec]:
    """自动发现 solver 下声明了 AUTO_STRATEGY_SPEC 的策略。"""
    discovered: Dict[str, StrategySpec] = {}
    caster_map: Dict[str, Callable[[Any], Any]] = {
        'int': int,
        'float': float,
        'str': str,
    }

    try:
        import solver
    except Exception:
        return discovered

    for mod in pkgutil.iter_modules(solver.__path__):
        if not mod.name.endswith('_strategy'):
            continue
        module_name = f"solver.{mod.name}"
        try:
            module = importlib.import_module(module_name)
            raw = getattr(module, 'AUTO_STRATEGY_SPEC', None)
            if not raw:
                continue

            key = str(raw.get('key', '')).strip()
            label = str(raw.get('label', '')).strip()
            runner_name = raw.get('runner')
            if not key or not label or not isinstance(runner_name, str):
                continue

            runner = globals().get(runner_name)
            if not callable(runner):
                continue

            parameters_raw = raw.get('parameters', []) or []
            parameters: list[StrategyParameter] = []
            for item in parameters_raw:
                caster_name = str(item.get('caster', 'str'))
                caster = caster_map.get(caster_name)
                if caster is None:
                    continue
                parameters.append(
                    StrategyParameter(
                        name=str(item.get('name', '')).strip(),
                        label=str(item.get('label', '')).strip(),
                        caster=caster,
                        default=item.get('default'),
                        description=str(item.get('description', '')).strip(),
                        required=bool(item.get('required', False)),
                    )
                )

            supported_trade_prices_raw = raw.get('supported_trade_prices', [TRADE_PRICE_OPEN])
            supported_trade_prices = tuple(str(v) for v in supported_trade_prices_raw)

            discovered[key] = StrategySpec(
                key=key,
                label=label,
                runner=runner,
                parameters=tuple(parameters),
                description=str(raw.get('description', '')).strip(),
                supported_trade_prices=supported_trade_prices if supported_trade_prices else (TRADE_PRICE_OPEN,),
            )
        except Exception:
            # 自动发现应是 best-effort，单个策略异常不应影响其他策略
            continue

    return discovered


def init(cache_dir: str = "data") -> None:
    """初始化后端（比如创建缓存目录）。"""
    os.makedirs(cache_dir, exist_ok=True)


def _fetch_data_for_backtest(symbol: str, source: object,
                              start_date: Optional[str], end_date: Optional[str]):
    """按日期范围获取回测所需数据的辅助函数。

    若未指定日期范围，则使用数据提供者的默认行为（返回全量数据）；
    否则传入哨兵日期以覆盖完整区间。

    Args:
        symbol: 股票代码
        source: 数据源
        start_date: 起始日期（可为 None）
        end_date: 结束日期（可为 None）

    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    if start_date is None and end_date is None:
        return get_data(symbol=symbol, source=source)
    return get_data(symbol=symbol, source=source,
                    start_date=start_date or "19700101",
                    end_date=end_date or "20500101")


def get_data(symbol: str = "600900",
             source: object = "auto",
             start_date: Optional[str] = None,
             end_date: Optional[str] = None,
             cache_dir: str = "data",
             max_attempts: int = 3,
             force_refresh: bool = False,
             buffer_days: int = 5):
    """获取数据，直接调用 `source.data_provider.get_data`。

    该函数是 tests 应该直接调用的入口。
    """
    sd = _validate_date_str(start_date)
    ed = _validate_date_str(end_date)

    normalized_start = _normalize_for_source(sd, source)
    normalized_end = _normalize_for_source(ed, source)

    # 如果没有传入日期参数，则不显式将 start_date/end_date 传给底层，使用底层默认行为（避免传 None 给 provider）
    if sd is None and ed is None:
        df = _get_data(symbol=symbol, source=source, cache_dir=cache_dir, max_attempts=max_attempts,
                       force_refresh=force_refresh, buffer_days=buffer_days)
    else:
        df = _get_data(symbol=symbol, source=source, start_date=normalized_start or start_date,
                       end_date=normalized_end or end_date, cache_dir=cache_dir, max_attempts=max_attempts,
                       force_refresh=force_refresh, buffer_days=buffer_days)

    # 无论底层如何返回（例如从缓存返回整表），在这里对返回的数据按传入的 start/end 进行二次过滤，
    # 以确保前端传入的时间段生效。
    try:
        import pandas as _pd
        if sd is not None or ed is not None:
            df = df.copy()
            if sd is not None:
                sd_dt = _pd.to_datetime(sd)
                df = df[df['date'] >= sd_dt]
            if ed is not None:
                ed_dt = _pd.to_datetime(ed)
                df = df[df['date'] <= ed_dt]
    except Exception:
        # 若过滤过程中出错，不阻塞原始行为，返回原始 df
        pass

    return df


def run_mean_cost(symbol: str = "600900", start_date: Optional[str] = None, end_date: Optional[str] = None,
                  lot_size: float = 100.0, init_cash: float = 100000.0, source: object = "auto", 
                  progress_callback: Optional[Callable[[int, int], None]] = None,
                  trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """调用均值成本模拟（封装自 solver.mean_cost_strategy.simulate_mean_cost）。"""
    if simulate_mean_cost is None:
        raise RuntimeError("mean_cost 模块不可用")
    return simulate_mean_cost(symbol=symbol, start_date=start_date, end_date=end_date, 
                            lot_size=lot_size, init_cash=init_cash, source=source,
                            progress_callback=progress_callback, trade_price=trade_price)


def run_fixed_amount(symbol: str = "600900",
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    fixed_amount: float = 1000.0,
                    lot_size: float = 100.0,
                    init_cash: float = 100000.0,
                    source: object = "auto",
                    progress_callback: Optional[Callable[[int, int], None]] = None,
                    trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """调用定投策略模拟（封装自 simulator.simulator.simulate_fixed_amount）。
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        fixed_amount: 每次定投金额（默认 1000 元）
        lot_size: 交易手数
        init_cash: 初始资金
        source: 数据源
        progress_callback: 进度回调函数
        
    Returns:
        包含回测结果的字典
    """
    if simulate_fixed_amount is None:
        raise RuntimeError("fixed_amount 模块不可用")
    return simulate_fixed_amount(symbol=symbol,
                                start_date=start_date,
                                end_date=end_date,
                                fixed_amount=fixed_amount,
                                lot_size=lot_size,
                                init_cash=init_cash,
                                source=source,
                                progress_callback=progress_callback,
                                trade_price=trade_price)


def run_sma_backtest(symbol: str = "600900", source: object = "auto",
                     start_date: Optional[str] = None, end_date: Optional[str] = None,
                     lot_size: float = 100.0, init_cash: float = 100000.0, period: int = 20,
                     progress_callback: Optional[Callable[[int, int], None]] = None,
                     trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """使用统一模拟器运行 SMA 回测并返回统一的展示结果。
    
    Args:
        symbol: 股票代码
        source: 数据源
        start_date: 开始日期
        end_date: 结束日期
        lot_size: 交易手数
        init_cash: 初始资金
        period: SMA 周期（默认 20）
        progress_callback: 进度回调函数
    """
    try:
        from simulator.simulator import simulate_sma
    except Exception as e:
        raise RuntimeError(f"SMA 模拟器不可用: {e}") from e

    # 以传入的日期范围优先；若未传则使用 get_data 的默认参数
    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    # 只保留回测所需字段
    df = df[["date", "open", "high", "low", "close", "volume"]]

    sim_res = simulate_sma(symbol=symbol, df=df, period=period, lot_size=lot_size,
                           init_cash=init_cash, progress_callback=progress_callback,
                           trade_price=trade_price)
    sim_res.setdefault('init_cash', init_cash)
    # 兼容旧调用方，沿用 final_cash 字段表达最终总资产。
    sim_res.setdefault('final_cash', sim_res.get('total_value', init_cash))
    return sim_res


def run_dual_ma_backtest(symbol: str = "600900", source: object = "auto",
                         start_date: Optional[str] = None, end_date: Optional[str] = None,
                         lot_size: float = 100.0, init_cash: float = 100000.0,
                         short_period: int = 5, long_period: int = 20,
                         progress_callback: Optional[Callable[[int, int], None]] = None,
                         trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """使用统一模拟器运行双均线交叉回测。"""
    if short_period <= 0 or long_period <= 0:
        raise ValueError('均线周期必须大于 0')
    if short_period >= long_period:
        raise ValueError('短期均线周期必须小于长期均线周期')

    from simulator.simulator import Simulator
    from solver.dual_ma_strategy import DualMaDecision

    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df["ma_short"] = df["close"].rolling(window=short_period, min_periods=short_period).mean()
    df["ma_long"] = df["close"].rolling(window=long_period, min_periods=long_period).mean()

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = DualMaDecision(short_period=short_period, long_period=long_period, df=df)
    sim_res = sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )
    sim_res.setdefault('init_cash', init_cash)
    sim_res.setdefault('final_cash', sim_res.get('total_value', init_cash))
    return sim_res


def run_bollinger_backtest(symbol: str = "600900", source: object = "auto",
                           start_date: Optional[str] = None, end_date: Optional[str] = None,
                           lot_size: float = 100.0, init_cash: float = 100000.0,
                           period: int = 20, std_multiplier: float = 2.0,
                           progress_callback: Optional[Callable[[int, int], None]] = None,
                           trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """使用统一模拟器运行布林带回测。"""
    if period <= 0:
        raise ValueError('布林带周期必须大于 0')
    if std_multiplier <= 0:
        raise ValueError('标准差倍数必须大于 0')

    from simulator.simulator import Simulator
    from solver.bollinger_strategy import BollingerDecision

    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    rolling = df["close"].rolling(window=period, min_periods=period)
    df["bollinger_mid"] = rolling.mean()
    df["bollinger_std"] = rolling.std(ddof=0)  # 使用总体标准差，保持与常见布林带口径一致
    df["bollinger_upper"] = df["bollinger_mid"] + std_multiplier * df["bollinger_std"]
    df["bollinger_lower"] = df["bollinger_mid"] - std_multiplier * df["bollinger_std"]

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = BollingerDecision(period=period, std_multiplier=std_multiplier, df=df)
    sim_res = sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )
    sim_res.setdefault('init_cash', init_cash)
    sim_res.setdefault('final_cash', sim_res.get('total_value', init_cash))
    return sim_res


def run_rsi_backtest(symbol: str = "600900", source: object = "auto",
                     start_date: Optional[str] = None, end_date: Optional[str] = None,
                     lot_size: float = 100.0, init_cash: float = 100000.0,
                     period: int = 14, oversold: float = 30.0, overbought: float = 70.0,
                     progress_callback: Optional[Callable[[int, int], None]] = None,
                     trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """使用统一模拟器运行 RSI 回测。"""
    if period <= 0:
        raise ValueError('RSI 周期必须大于 0')
    if not 0 <= oversold < overbought <= 100:
        raise ValueError('RSI 阈值必须满足 0 <= oversold < overbought <= 100')

    from simulator.simulator import Simulator
    from solver.rsi_strategy import RsiDecision

    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.where(avg_loss != 0)
    df["rsi"] = 100 - (100 / (1 + rs))
    df.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100.0
    df.loc[(avg_loss == 0) & (avg_gain == 0), "rsi"] = 50.0

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    strategy = RsiDecision(period=period, oversold=oversold, overbought=overbought, df=df)
    sim_res = sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )
    sim_res.setdefault('init_cash', init_cash)
    sim_res.setdefault('final_cash', sim_res.get('total_value', init_cash))
    return sim_res


def run_futures_a50_prev_night(symbol: str = "600900", source: object = "auto",
                               start_date: Optional[str] = None, end_date: Optional[str] = None,
                               lot_size: float = 100.0, init_cash: float = 100000.0,
                               futures_symbol: str = "CN00Y",
                               base_position_lots: int = 2,
                               progress_callback: Optional[Callable[[int, int], None]] = None,
                               trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """前一晚 A50 涨跌信号策略：上涨则买入并预约1小时后卖出。"""
    try:
        from simulator.simulator import Simulator
        from solver.futures_open_hour_strategy import FuturesOpenHourDecision
    except Exception as e:
        raise RuntimeError(f"A50 策略模块不可用: {e}") from e

    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)

    df = df[["date", "open", "high", "low", "close", "volume"]]

    strategy = FuturesOpenHourDecision(futures_symbol=futures_symbol, source=source)
    # 运行前尝试确认能获取到期货数据，若无法获取则给出友好错误提示，避免回测悄悄无成交。
    try:
        futures_df = get_data(symbol=futures_symbol, source=source, cache_dir='data')
    except Exception:
        futures_df = None

    if futures_df is None or getattr(futures_df, 'empty', False):
        raise RuntimeError(
            f"无法获取期货数据: {futures_symbol}. 策略需要前一晚的期货收盘价以生成买入信号。\n"
            "请确认已在本地缓存该期货数据（data/ 目录）或在 web 界面中指定可用的 futures_symbol。"
        )

    # 将已获取的期货数据注入决策器，避免在回测循环中重复下载
    strategy.futures_df = futures_df

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
    return sim.simulate(
        df=df,
        strategy=strategy,
        symbol=symbol,
        progress_callback=progress_callback,
        trade_price=trade_price,
        granularity='1h',
        enable_scheduled_orders=True,
        enforce_t_plus_one=True,
        require_base_position_for_t_plus_one_intraday=True,
        base_position_lots=base_position_lots,
        mode='backtest',
    )


def _build_strategy_registry() -> Dict[str, StrategySpec]:
    """构建策略注册表。"""
    registry = {
        'sma': StrategySpec(
            key='sma',
            label='SMA',
            runner=run_sma_backtest,
            parameters=(
                StrategyParameter(
                    name='period',
                    label='SMA 周期',
                    caster=int,
                    default=20,
                    description='移动平均线周期',
                ),
            ),
            description='基于移动平均线的趋势策略',
        ),
        'mean_cost': StrategySpec(
            key='mean_cost',
            label='均值成本',
            runner=run_mean_cost,
            description='围绕持仓均价进行开盘交易',
        ),
        'fixed_amount': StrategySpec(
            key='fixed_amount',
            label='定投',
            runner=run_fixed_amount,
            parameters=(
                StrategyParameter(
                    name='fixed_amount',
                    label='每次定投金额',
                    caster=float,
                    default=1000.0,
                    description='每次开盘投入的金额',
                ),
            ),
            description='固定金额定投策略',
        ),
    }

    # 自动接入：扫描 solver 下声明了 AUTO_STRATEGY_SPEC 的策略
    registry.update(_discover_auto_strategy_specs())
    return registry


def list_strategy_specs() -> list[StrategySpec]:
    """返回当前所有已注册策略。"""
    return list(_build_strategy_registry().values())


def get_strategy_spec(strategy: str) -> StrategySpec:
    """按策略名获取策略规格。"""
    registry = _build_strategy_registry()
    if strategy not in registry:
        raise ValueError(f"不支持的策略: {strategy}")
    return registry[strategy]


def create_backtest_request(symbol: str = '600900',
                            strategy: str = 'sma',
                            source: object = 'auto',
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            lot_size: float = 100.0,
                            init_cash: float = 100000.0,
                            trade_price: str = TRADE_PRICE_OPEN,
                            strategy_params: Optional[Mapping[str, Any]] = None,
                            progress_callback: Optional[Callable[[int, int], None]] = None) -> BacktestRequest:
    """构造并校验统一回测请求。"""
    spec = get_strategy_spec(strategy)
    if trade_price not in SUPPORTED_TRADE_PRICE_FIELDS:
        raise ValueError(f"不支持的交易价格字段: {trade_price}")
    if trade_price not in spec.supported_trade_prices:
        raise ValueError(f"策略 {strategy} 当前仅支持以下交易价格字段: {', '.join(spec.supported_trade_prices)}")

    request = BacktestRequest(
        symbol=str(symbol).strip() or '600900',
        strategy=strategy,
        source=source,
        start_date=_validate_date_str(start_date),
        end_date=_validate_date_str(end_date),
        lot_size=float(lot_size),
        init_cash=float(init_cash),
        trade_price=trade_price,
        strategy_params=_normalize_strategy_params(spec, strategy_params),
        progress_callback=progress_callback,
    )

    if request.start_date and request.end_date and request.start_date > request.end_date:
        raise ValueError('起始日期不能晚于结束日期')
    if request.lot_size <= 0:
        raise ValueError('交易手数必须大于 0')
    if request.init_cash <= 0:
        raise ValueError('初始资金必须大于 0')

    return request


def run_backtest(backtest_request: BacktestRequest | Mapping[str, Any]) -> Dict[str, Any]:
    """统一的回测执行入口。"""
    if isinstance(backtest_request, BacktestRequest):
        request = backtest_request
    else:
        request = create_backtest_request(**dict(backtest_request))

    spec = get_strategy_spec(request.strategy)
    return spec.runner(
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        lot_size=request.lot_size,
        init_cash=request.init_cash,
        source=request.source,
        progress_callback=request.progress_callback,
        trade_price=request.trade_price,
        **request.strategy_params,
    )


if __name__ == '__main__':
    # 方便开发时直接运行并快速检查
    try:
        init()
        print('stocks backend initialized')
    except Exception:
        traceback.print_exc()
