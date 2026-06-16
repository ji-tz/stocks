"""模拟盘交易引擎 — 后台线程定时拉行情→跑策略→执行交易。

提供 PaperTradeEngine 类，支持：
  1. configure() — 配置策略、标的、参数
  2. start() — 创建会话，启动后台线程
  3. stop() — 停止后台线程
  4. get_status() / get_trades() — 查询状态和交易记录

线程安全：所有状态读写通过 threading.Lock() 保护。
"""

import threading
import time
import logging
from datetime import datetime
from typing import Any, Optional

from exchange.realtime.exchange import RealtimeSimExchange
from exchange.source.data_provider import get_data
from trader.stocks import get_strategy_spec
from trader import persistence as _persistence

logger = logging.getLogger(__name__)


class PaperTradeEngine:
    """模拟盘交易引擎 — 后台线程定时拉行情→跑策略→执行交易。"""

    STATUS_IDLE = 'idle'
    STATUS_RUNNING = 'running'
    STATUS_STOPPED = 'stopped'

    def __init__(self):
        self._lock = threading.Lock()
        self._status = self.STATUS_IDLE
        self._session_id: Optional[int] = None
        self._strategy_key = ''
        self._stock_code = ''
        self._params: dict = {}
        self._init_cash = 100000.0
        self._lot_size = 100.0
        self._source = 'auto'
        self._interval_seconds = 300
        self._exchange: Optional[RealtimeSimExchange] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_price = 0.0
        self._last_update = ''
        self._trade_count = 0

    # ── Configuration ──────────────────────────────────────

    def configure(self, strategy_key: str, stock_code: str,
                  params: Optional[dict] = None,
                  init_cash: float = 100000.0,
                  lot_size: float = 100.0,
                  source: str = 'auto',
                  interval_seconds: int = 300) -> None:
        """Store config and create RealtimeSimExchange instance.

        Args:
            strategy_key: 策略 key（如 'sma', 'dual_ma'）
            stock_code: 股票代码（如 '600900'）
            params: 策略参数字典
            init_cash: 初始资金
            lot_size: 每手股数
            source: 数据源（'auto' 自动选择）
            interval_seconds: 轮询间隔（秒）
        """
        with self._lock:
            self._strategy_key = strategy_key
            self._stock_code = stock_code
            self._params = params or {}
            self._init_cash = init_cash
            self._lot_size = lot_size
            self._source = source
            self._interval_seconds = interval_seconds
            self._exchange = RealtimeSimExchange(
                stock_code=stock_code,
                init_cash=init_cash,
                lot_size=lot_size,
            )

    # ── Lifecycle ──────────────────────────────────────────

    def start(self) -> bool:
        """Start background paper trading thread.

        Returns:
            True if started, False if already running.
        """
        with self._lock:
            if self._status == self.STATUS_RUNNING:
                return False
            self._status = self.STATUS_RUNNING
            self._stop_event.clear()
            self._trade_count = 0

            # Create session in persistence DB
            sid = _persistence.save_paper_session(
                strategy_key=self._strategy_key,
                stock_code=self._stock_code,
                params=self._params,
                init_cash=self._init_cash,
                lot_size=self._lot_size,
                source=self._source,
                interval_seconds=self._interval_seconds,
                status=self.STATUS_RUNNING,
            )
            self._session_id = sid

            # Start background loop thread
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        """Stop background thread and update session status.

        Returns:
            True if stopped, False if not running.
        """
        with self._lock:
            if self._status != self.STATUS_RUNNING:
                return False
            self._stop_event.set()

        # Join thread with timeout
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        with self._lock:
            self._status = self.STATUS_STOPPED
            if self._session_id is not None:
                _persistence.update_paper_session(
                    session_id=self._session_id,
                    status=self.STATUS_STOPPED,
                )
        return True

    # ── Query ──────────────────────────────────────────────

    def get_status(self) -> dict:
        """Return thread-safe snapshot of current state.

        Returns:
            dict with keys: status, session_id, stock_code, strategy_key,
            last_price, last_update, account (dict), trade_count.
        """
        with self._lock:
            account_info: dict[str, Any] = {}
            if self._exchange is not None:
                price = self._last_price if self._last_price > 0 else 1.0
                summary = self._exchange.get_summary(price)
                account_info = {
                    'cash': summary['cash'],
                    'shares': summary['shares'],
                    'avg_cost': summary['avg_cost'],
                    'market_value': summary['market_value'],
                    'total_value': summary['total_value'],
                    'realized_pl': summary['realized_pl'],
                    'unrealized_pl': summary['unrealized_pl'],
                }
            return {
                'status': self._status,
                'session_id': self._session_id,
                'stock_code': self._stock_code,
                'strategy_key': self._strategy_key,
                'last_price': self._last_price,
                'last_update': self._last_update,
                'account': account_info,
                'trade_count': self._trade_count,
            }

    def get_trades(self, limit: int = 50) -> list:
        """Return last N trades from persistence for the current session."""
        if self._session_id is None:
            return []
        return _persistence.get_paper_trades(
            session_id=self._session_id, limit=limit,
        )

    # ── Internal: background loop ──────────────────────────

    def _run_loop(self) -> None:
        """Main background loop: tick every interval_seconds."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.error("Paper trade tick error: %s", exc)
            # Sleep for interval, but wake early if stop requested
            self._stop_event.wait(timeout=self._interval_seconds)

    def _tick(self) -> dict:
        """Single iteration: fetch data, run strategy, execute trade.

        Returns:
            dict with keys: trade_executed, signal, price, reason.
        """
        result: dict[str, Any] = {
            'trade_executed': False,
            'signal': None,
            'price': 0.0,
            'reason': '',
        }

        # Snapshot current config under lock
        with self._lock:
            if self._exchange is None:
                result['reason'] = 'not configured'
                return result
            exchange = self._exchange
            strategy_key = self._strategy_key
            stock_code = self._stock_code
            source = self._source
            strategy_params = dict(self._params)

        # Get signal from strategy
        signal_result = self._run_strategy_signal(
            strategy_key, stock_code, strategy_params, source, exchange,
        )
        result['signal'] = signal_result.get('signal')
        result['price'] = signal_result.get('price', 0.0)
        result['reason'] = signal_result.get('reason', '')

        # Execute trade if signal is buy or sell
        signal = signal_result.get('signal')
        if signal in ('buy', 'sell'):
            price = signal_result.get('price', 0.0)
            trade_date = signal_result.get('date', datetime.now())
            if price <= 0:
                result['reason'] = 'invalid price'
            else:
                with self._lock:
                    if signal == 'buy':
                        trade_result = exchange.buy(trade_date, price)
                    else:
                        trade_result = exchange.sell(trade_date, price)

                if trade_result.success:
                    self._trade_count += 1
                    result['trade_executed'] = True
                    result['reason'] = ''

                    # Calculate cost and total value
                    actual_shares = (
                        trade_result.order.shares
                        if trade_result.order else self._lot_size
                    )
                    cost = price * actual_shares
                    # Compute total_value after trade
                    with self._lock:
                        total_val = exchange.get_summary(price)['total_value']

                    # Persist the trade
                    if self._session_id is not None:
                        ts = (
                            trade_date.strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(trade_date, 'strftime')
                            else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                        _persistence.save_paper_trade(
                            session_id=self._session_id,
                            trade_time=ts,
                            action=signal,
                            price=price,
                            shares=actual_shares,
                            cost=cost,
                            realized_pl=trade_result.realized_pl,
                            cash_after=trade_result.cash_after,
                            shares_after=trade_result.shares_after,
                            total_value=total_val,
                        )
                else:
                    result['reason'] = trade_result.message

        # Update last price
        with self._lock:
            self._last_price = result['price']
            self._last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return result

    # ── Internal: data & signal helpers ────────────────────

    def _get_latest_price(self, symbol: str, source: str) -> float:
        """Get latest close price from data provider."""
        try:
            df = get_data(symbol=symbol, source=source)
            if df is None or df.empty:
                return 0.0
            return float(df['close'].iloc[-1])
        except Exception:
            return 0.0

    def _run_strategy_signal(
        self,
        strategy_key: str,
        symbol: str,
        params: dict,
        source: str,
        exchange: RealtimeSimExchange,
    ) -> dict:
        """Get latest data, prepare, and generate signal.

        For module_interface strategies: prepare_backtest_data → create_strategy → decide.
        For simple runner-based strategies: run full backtest and extract last signal.

        Returns:
            dict with keys: signal ('buy'/'sell'/'hold'/None), price, date, reason.
        """
        import importlib

        # Resolve strategy spec
        try:
            spec = get_strategy_spec(strategy_key)
        except ValueError as exc:
            return {'signal': None, 'price': 0.0, 'reason': str(exc)}

        # Fetch data
        try:
            df = get_data(symbol=symbol, source=source)
        except Exception as exc:
            return {'signal': None, 'price': 0.0, 'reason': f'data error: {exc}'}

        if df is None or df.empty:
            return {'signal': None, 'price': 0.0, 'reason': 'no data'}

        # ── Module-interface strategies ──
        if spec.module_interface and spec.module_name:
            try:
                module = importlib.import_module(spec.module_name)

                # prepare_backtest_data
                prepared_df = df.copy()
                prepare_fn = getattr(module, 'prepare_backtest_data', None)
                if callable(prepare_fn):
                    prepared_df = prepare_fn(df=prepared_df, source=source, **params)

                # create_strategy
                create_fn = getattr(module, 'create_strategy', None)
                if not callable(create_fn):
                    return {
                        'signal': None, 'price': 0.0,
                        'reason': 'module missing create_strategy()',
                    }
                strategy = create_fn(df=prepared_df, source=source, **params)

                # Latest bar
                latest = prepared_df.iloc[-1]
                latest_price = float(latest['close'])
                pos = exchange.account.position

                # Call decide()
                sig = strategy.decide(
                    open_price=float(latest['open']),
                    close_price=latest_price,
                    avg_cost=pos.avg_cost,
                    shares=pos.shares,
                    date=latest['date'],
                    cash=exchange.account.cash,
                )

                return {
                    'signal': sig,
                    'price': latest_price,
                    'date': latest['date'],
                    'reason': '' if sig else 'hold',
                }

            except Exception as exc:
                return {
                    'signal': None, 'price': 0.0,
                    'reason': f'strategy error: {exc}',
                }

        # ── Simple runner-based strategies ──
        try:
            sim_res = spec.runner(
                symbol=symbol,
                source=source,
                lot_size=self._lot_size,
                init_cash=exchange.account.cash,
                start_date=None,
                end_date=None,
                **params,
            )
            trades_list = sim_res.get('trades_list', [])
            last_price = sim_res.get('last_price', 0.0)

            if trades_list:
                last_trade = trades_list[-1]
                action = last_trade.get('action')
                if action in ('buy', 'sell'):
                    return {
                        'signal': action,
                        'price': last_trade.get('price', last_price),
                        'date': last_trade.get('date', datetime.now().strftime('%Y-%m-%d')),
                        'reason': '',
                    }

            return {
                'signal': None,
                'price': last_price,
                'reason': 'hold',
            }

        except Exception as exc:
            return {
                'signal': None, 'price': 0.0,
                'reason': f'runner error: {exc}',
            }


# ── Module-level singleton ─────────────────────────────────

engine = PaperTradeEngine()
"""Module-level singleton that can be imported by web.py."""


