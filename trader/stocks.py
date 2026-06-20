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
from functools import partial
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, Mapping

from exchange.source.data_provider import get_data as _get_data
import logging

logger = logging.getLogger(__name__)

try:
    from trader.simulator import simulate_mean_cost, simulate_fixed_amount
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
    icon: str = '📌'
    template: str = 'strategy_config.html'
    supported_trade_prices: tuple[str, ...] = (TRADE_PRICE_OPEN,)
    module_name: Optional[str] = None
    module_interface: bool = False


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
    """自动发现 strategy 下声明了 AUTO_STRATEGY_SPEC 的策略。"""
    discovered: Dict[str, StrategySpec] = {}
    caster_map: Dict[str, Callable[[Any], Any]] = {
        'int': int,
        'float': float,
        'str': str,
    }

    try:
        import strategy
    except Exception:
        logger.debug("策略模块不可用，跳过自动发现")
        return discovered

    for mod in pkgutil.iter_modules(strategy.__path__):
        if not mod.name.endswith('_strategy'):
            continue
        module_name = f"strategy.{mod.name}"
        try:
            module = importlib.import_module(module_name)
            raw = getattr(module, 'AUTO_STRATEGY_SPEC', None)
            if not raw:
                continue

            key = str(raw.get('key', '')).strip()
            label = str(raw.get('label', '')).strip()
            runner_name = raw.get('runner')
            module_interface = bool(raw.get('module_interface', False))
            if not key or not label or not isinstance(runner_name, str):
                continue

            runner = globals().get(runner_name)
            if not callable(runner):
                continue
            if module_interface:
                runner = partial(runner, strategy_key=key)

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
                icon=str(raw.get('icon', '📌')),
                template=str(raw.get('template', 'strategy_config.html')),
                supported_trade_prices=supported_trade_prices if supported_trade_prices else (TRADE_PRICE_OPEN,),
                module_name=module_name,
                module_interface=module_interface,
            )
        except Exception:
            # 自动发现应是 best-effort，单个策略异常不应影响其他策略
            logger.debug("策略 %s 自动发现异常", module_name, exc_info=True)
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

    如果指定了 start_date 但返回数据为空，会自动尝试将 end_date 扩展到
    未来以查找第一个有数据的交易日，避免因 start_date 落在非交易日
    （周末/节假日）导致回测无法开始。

    Args:
        symbol: 股票代码
        source: 数据源
        start_date: 起始日期（可为 None）
        end_date: 结束日期（可为 None）

    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    import pandas as _pd

    if start_date is None and end_date is None:
        return get_data(symbol=symbol, source=source)

    safe_start = start_date or "19700101"
    safe_end = end_date or "20500101"

    df = get_data(symbol=symbol, source=source,
                  start_date=safe_start, end_date=safe_end)

    # 如果数据为空且用户指定了起始日期，尝试去掉 end_date 限制查找下一个交易日
    if df.empty and start_date is not None:
        logger.info(
            "回测时间范围 %s ~ %s 无交易日数据，"
            "自动向前扩展查找下一个交易日",
            safe_start, safe_end,
        )
        # 去掉 end_date 限制，只保留 start_date 约束，查找下一个交易日
        df = get_data(symbol=symbol, source=source,
                      start_date=safe_start, end_date="20500101")
        if not df.empty:
            actual_first = _pd.to_datetime(df["date"].iloc[0]).strftime("%Y-%m-%d")
            logger.info(
                "回测实际起始日期调整为 %s（原始起始 %s 无交易日数据）",
                actual_first, str(start_date),
            )
        else:
            logger.warning(
                "即使在最大时间范围内也未找到 %s 的交易日数据，"
                "请检查股票代码或数据源",
                safe_start,
            )

    # 如果指定了结束日期但最后一个交易日早于结束日期（非交易日），截断数据
    if end_date is not None and not df.empty:
        last_trade_date = _pd.to_datetime(df["date"].iloc[-1])
        end_dt = _pd.to_datetime(end_date)
        if last_trade_date < end_dt:
            actual_last = last_trade_date.strftime("%Y-%m-%d")
            logger.info(
                "回测实际结束日期调整为 %s（原始结束 %s 无交易日数据）",
                actual_last, str(end_date),
            )
            df = df[df["date"] <= last_trade_date]

    return df


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
                # 如果数据不为空但第一个交易日晚于请求的起始日期，记录警告
                if not df.empty and start_date is not None:
                    actual_first = _pd.to_datetime(df['date'].iloc[0])
                    if actual_first > sd_dt:
                        diff_days = (actual_first - sd_dt).days
                        logger.info(
                            "起始日期 %s 为非交易日，实际回测从下一个交易日 %s 开始（延迟 %d 天）",
                            sd, actual_first.strftime('%Y-%m-%d'), diff_days,
                        )
            if ed is not None:
                ed_dt = _pd.to_datetime(ed)
                df = df[df['date'] <= ed_dt]
    except Exception:
        # 若过滤过程中出错，不阻塞原始行为，返回原始 df
        logger.debug("日期范围过滤出错", exc_info=True)
        pass

    return df


def run_mean_cost(symbol: str = "600900", start_date: Optional[str] = None, end_date: Optional[str] = None,
                  lot_size: float = 100.0, init_cash: float = 100000.0, source: object = "auto",
                  progress_callback: Optional[Callable[[int, int], None]] = None,
                  trade_price: str = TRADE_PRICE_OPEN) -> Dict[str, Any]:
    """调用均值成本模拟（封装自 strategy.mean_cost_strategy.simulate_mean_cost）。"""
    if simulate_mean_cost is None:
        raise RuntimeError("mean_cost 模块不可用")
    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    return simulate_mean_cost(symbol=symbol, df=df,
                              lot_size=lot_size, init_cash=init_cash,
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
    """调用定投策略模拟（封装自 strategy.fixed_amount_strategy.simulate_fixed_amount）。

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
    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    return simulate_fixed_amount(symbol=symbol, df=df,
                                 fixed_amount=fixed_amount,
                                 lot_size=lot_size, init_cash=init_cash,
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
        from trader.simulator import simulate_sma
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


def run_module_strategy_backtest(symbol: str = "600900", source: object = "auto",
                                 start_date: Optional[str] = None, end_date: Optional[str] = None,
                                 lot_size: float = 100.0, init_cash: float = 100000.0,
                                 progress_callback: Optional[Callable[[int, int], None]] = None,
                                 trade_price: str = TRADE_PRICE_OPEN,
                                 strategy_key: str = '',
                                 **strategy_params: Any) -> Dict[str, Any]:
    """执行自动注册策略模块的统一回测流程。

    流程如下：
    1. 根据 `strategy_key` 找到自动注册的策略模块；
    2. 调用模块内可选的 `validate_strategy_parameters(**params)` 做参数校验；
    3. 获取标准 OHLCV 数据，并调用可选的 `prepare_backtest_data(df, **params)` 预处理指标；
    4. 调用模块必须实现的 `create_strategy(df, **params)` 构造决策器；
    5. 统一交给 `Simulator.simulate()` 执行回测。

    Args:
        symbol: 回测标的代码。
        source: 数据源。
        start_date: 起始日期。
        end_date: 结束日期。
        lot_size: 交易手数。
        init_cash: 初始资金。
        progress_callback: 回测进度回调。
        trade_price: 成交价格字段。
        strategy_key: 自动注册策略唯一标识。
        strategy_params: 策略模块自定义参数。

    Returns:
        统一格式的回测结果字典。
    """
    if not strategy_key:
        raise ValueError('strategy_key 不能为空')

    spec = get_strategy_spec(strategy_key)
    if not spec.module_name:
        raise RuntimeError(f'策略 {strategy_key} 缺少模块信息，无法走通用回测流程')

    module = importlib.import_module(spec.module_name)

    validate_parameters = getattr(module, 'validate_strategy_parameters', None)
    if callable(validate_parameters):
        try:
            validate_parameters(**strategy_params)
        except ValueError as exc:
            raise ValueError(f'策略 {strategy_key} 参数校验失败: {exc}') from exc

    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()

    prepare_backtest_data = getattr(module, 'prepare_backtest_data', None)
    if callable(prepare_backtest_data):
        df = prepare_backtest_data(df=df, source=source, **strategy_params)

    create_strategy = getattr(module, 'create_strategy', None)
    if not callable(create_strategy):
        raise RuntimeError(f'策略模块 {spec.module_name} 缺少 create_strategy()')

    strategy = create_strategy(df=df, source=source, **strategy_params)

    from trader.simulator import Simulator

    sim = Simulator(lot_size=lot_size, init_cash=init_cash)
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
        from trader.simulator import Simulator
        from strategy.futures_open_hour_strategy import FuturesOpenHourDecision
    except Exception as e:
        raise RuntimeError(f"A50 策略模块不可用: {e}") from e

    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)

    df = df[["date", "open", "high", "low", "close", "volume"]]

    strategy = FuturesOpenHourDecision(futures_symbol=futures_symbol, source=source)
    # 运行前尝试确认能获取到期货数据，若无法获取则给出友好错误提示，避免回测悄悄无成交。
    try:
        futures_df = get_data(symbol=futures_symbol, source=source, cache_dir='data')
    except Exception:
        logger.debug("期货数据获取失败", exc_info=True)
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


def run_signal_template(
    symbol: str = "600900",
    source: object = "auto",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lot_size: float = 100.0,
    init_cash: float = 100000.0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    trade_price: str = TRADE_PRICE_OPEN,
    buy_trigger: str = 'price_below',
    buy_price_value: float = 0.0,
    buy_exec_mode: str = 'all_in',
    buy_fixed_amount: float = 10000.0,
    buy_position_pct: float = 30.0,
    take_profit_pct: float = 0.0,
    stop_loss_pct: float = 0.0,
    sell_trigger: str = 'price_above',
    sell_price_value: float = 0.0,
    sell_profit_pct: float = 0.0,
    sell_loss_pct: float = 0.0,
    sell_exec_mode: str = 'all',
    sell_fixed_shares: float = 100.0,
    sell_ratio_pct: float = 50.0,
) -> Dict[str, Any]:
    """模板化买卖信号策略：按前端配置执行。"""
    try:
        from trader.simulator import simulate_signal_template
        from strategy.signal_template_strategy import SignalTemplateDecision
    except Exception as e:
        raise RuntimeError(f"信号模板策略模块不可用: {e}") from e

    if start_date is None and end_date is None:
        df = get_data(symbol=symbol, source=source)
    else:
        df = get_data(
            symbol=symbol,
            source=source,
            start_date=start_date or "19700101",
            end_date=end_date or "20500101")

    df = df[["date", "open", "high", "low", "close", "volume"]]
    feature_df = SignalTemplateDecision.build_features(df)

    strategy = SignalTemplateDecision(
        df=feature_df,
        lot_size=float(lot_size),
        buy_trigger=buy_trigger,
        buy_price_value=float(buy_price_value),
        buy_exec_mode=buy_exec_mode,
        buy_fixed_amount=float(buy_fixed_amount),
        buy_position_pct=float(buy_position_pct),
        take_profit_pct=float(take_profit_pct),
        stop_loss_pct=float(stop_loss_pct),
        sell_trigger=sell_trigger,
        sell_price_value=float(sell_price_value),
        sell_profit_pct=float(sell_profit_pct),
        sell_loss_pct=float(sell_loss_pct),
        sell_exec_mode=sell_exec_mode,
        sell_fixed_shares=float(sell_fixed_shares),
        sell_ratio_pct=float(sell_ratio_pct),
    )

    sim_res = simulate_signal_template(
        symbol=symbol,
        df=feature_df,
        strategy=strategy,
        lot_size=lot_size,
        init_cash=init_cash,
        progress_callback=progress_callback,
        trade_price=trade_price,
    )
    sim_res.setdefault('init_cash', init_cash)
    sim_res.setdefault('final_cash', sim_res.get('total_value', init_cash))
    return sim_res


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
            icon='📈',
        ),
        'mean_cost': StrategySpec(
            key='mean_cost',
            label='均值成本',
            runner=run_mean_cost,
            description='围绕持仓均价进行开盘交易',
            icon='💰',
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
            icon='🎯',
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


# ---------------------------------------------------------------------------
# 导出接口（回测结果 → Excel / PDF 数据准备）
# ---------------------------------------------------------------------------


def export_backtest_excel(
    backtest_result: Dict[str, Any],
    output_dir: str = "trader/exports",
    strategy_name: str = "",
) -> str:
    """将回测结果导出为 Excel 文件。

    Args:
        backtest_result: simulator 返回的回测结果字典。
        output_dir: 输出目录（默认 trader/exports）。
        strategy_name: 策略名称。

    Returns:
        生成的 Excel 文件路径。
    """
    from trader.export import export_to_excel, generate_filename

    symbol = backtest_result.get("symbol", "UNKNOWN")
    start_date = backtest_result.get("start_date", "")
    end_date = backtest_result.get("end_date", "")
    fname = generate_filename(symbol, strategy_name, start_date, end_date, ext="xlsx")
    output_path = os.path.join(output_dir, fname)
    return export_to_excel(backtest_result, output_path, strategy_name=strategy_name)


def export_prepare_pdf_data(
    backtest_result: Dict[str, Any],
    strategy_name: str = "",
) -> Dict[str, Any]:
    """准备回测结果的 PDF 导出数据。

    Args:
        backtest_result: simulator 返回的回测结果字典。
        strategy_name: 策略名称。

    Returns:
        包含 summary / metrics / trades 的结构化字典。
    """
    from trader.export import prepare_pdf_data

    return prepare_pdf_data(backtest_result, strategy_name=strategy_name)


# ---------------------------------------------------------------------------
# 多策略对比回测
# ---------------------------------------------------------------------------


def run_multi_strategy_backtest(
    symbol: str = "600900",
    source: object = "auto",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lot_size: float = 100.0,
    init_cash: float = 100000.0,
    trade_price: str = TRADE_PRICE_OPEN,
    strategies: Optional[list[str]] = None,
    strategies_params: Optional[dict[str, dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """多策略对比回测：一次获取行情数据，多个策略共享运行。

    Args:
        symbol: 股票代码
        source: 数据源
        start_date: 起始日期
        end_date: 结束日期
        lot_size: 交易手数
        init_cash: 初始资金
        trade_price: 成交价格字段
        strategies: 策略 key 列表（如 ['sma', 'dual_ma', 'rsi']）
        strategies_params: 各策略专属参数 {key: {param: value}}
        progress_callback: 进度回调

    Returns:
        {
            'symbol': str,
            'start_date': str,
            'end_date': str,
            'strategies': [
                {
                    'key': str,
                    'label': str,
                    'metrics': { ... },
                    'history': [ ... ],
                    'trades_list': [ ... ],
                    'init_cash': float,
                    'final_cash': float,
                },
                ...
            ]
        }
    """
    if not strategies:
        raise ValueError("strategies 列表不能为空")

    strategies_params = strategies_params or {}

    # 1. 只获取一次行情数据
    df = _fetch_data_for_backtest(symbol=symbol, source=source, start_date=start_date, end_date=end_date)

    start_date_str = ""
    end_date_str = ""
    try:
        import pandas as _pd
        if not df.empty and 'date' in df.columns:
            start_date_str = str(_pd.to_datetime(df['date'].iloc[0]).strftime('%Y-%m-%d'))
            end_date_str = str(_pd.to_datetime(df['date'].iloc[-1]).strftime('%Y-%m-%d'))
    except Exception:
        logger.debug("无法从DataFrame提取日期范围")

    results: list[dict[str, Any]] = []
    total = len(strategies)

    for idx, strategy_key in enumerate(strategies):
        if progress_callback:
            progress_callback(idx, total)

        spec = get_strategy_spec(strategy_key)
        params = strategies_params.get(strategy_key, {})

        try:
            if spec.module_interface and spec.module_name:
                # 自动注册的策略模块走通用流程
                from trader.simulator import Simulator

                module = importlib.import_module(spec.module_name)

                validate_parameters = getattr(module, 'validate_strategy_parameters', None)
                if callable(validate_parameters):
                    validate_parameters(**params)

                df_copy = df[["date", "open", "high", "low", "close", "volume"]].copy()

                prepare_backtest_data = getattr(module, 'prepare_backtest_data', None)
                if callable(prepare_backtest_data):
                    df_copy = prepare_backtest_data(df=df_copy, source=source, **params)

                create_strategy = getattr(module, 'create_strategy', None)
                if not callable(create_strategy):
                    raise RuntimeError(f'策略模块 {spec.module_name} 缺少 create_strategy()')

                strategy = create_strategy(df=df_copy, source=source, **params)

                sim = Simulator(lot_size=lot_size, init_cash=init_cash)
                sim_res = sim.simulate(
                    df=df_copy,
                    strategy=strategy,
                    symbol=symbol,
                    trade_price=trade_price,
                )
                sim_res.setdefault('init_cash', init_cash)
                sim_res.setdefault('final_cash', sim_res.get('total_value', init_cash))
            else:
                # 简单策略 runner
                sim_res = spec.runner(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    lot_size=lot_size,
                    init_cash=init_cash,
                    source=source,
                    trade_price=trade_price,
                    **params,
                )
        except Exception as e:
            sim_res = {
                'error': str(e),
                'symbol': symbol,
                'init_cash': init_cash,
            }

        sim_res['strategy_key'] = strategy_key
        sim_res['strategy_label'] = spec.label
        results.append(sim_res)

    return {
        'symbol': symbol,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'strategies': results,
    }


if __name__ == '__main__':
    # 方便开发时直接运行并快速检查
    try:
        init()
        print('stocks backend initialized')
    except Exception:
        traceback.print_exc()
