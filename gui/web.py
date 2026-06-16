import os
import sys
import json
import threading
import pandas as pd
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, session, jsonify, Response

# Ensure project root is on sys.path so sibling packages (e.g. `source`) can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trader.stocks as stocks
from trader.export import export_to_excel, prepare_pdf_data, generate_filename
from gui.backtest_progress import get_progress_manager
from trader import persistence

app = Flask(__name__, template_folder='templates')
# 使用环境变量配置secret_key，开发环境使用默认值
app.secret_key = os.environ.get('SECRET_KEY', 'stocks-quantitative-backtest-secret-key-2024')

# 在应用启动时加载股票列表到内存，避免重复文件IO
_STOCK_LIST = None
_STOCK_INDEX = None
_DOWNLOAD_SOURCES = ('akshare', 'baostock', 'tencent', 'sina', 'sohu', 'eastmoney', 'cailianpress', 'stooq')


def _get_cache_dir() -> str:
    """返回项目内的数据缓存目录绝对路径。"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def _validate_optional_date_range(start: str, end: str) -> tuple[str, str]:
    """校验可选日期范围，支持空字符串与 YYYYMMDD。"""
    import re

    start = (start or '').strip()
    end = (end or '').strip()
    date_pattern = re.compile(r'^\d{8}$')

    if start and not date_pattern.match(start):
        raise ValueError('起始日期格式必须为YYYYMMDD')
    if end and not date_pattern.match(end):
        raise ValueError('结束日期格式必须为YYYYMMDD')
    if start and end and start > end:
        raise ValueError('起始日期不能晚于结束日期')

    return start, end


def _build_stock_chart_payload(stock_code: str, start: str = '', end: str = '', source: str = 'auto') -> dict:
    """构造时间段页面的日线开盘价走势图数据。"""
    cache_dir = _get_cache_dir()
    df = stocks.get_data(
        symbol=stock_code,
        source=source,
        start_date=start or None,
        end_date=end or None,
        cache_dir=cache_dir,
    )

    if df is None or df.empty:
        raise RuntimeError('无法获取该时间段的股票日线数据')

    return _build_payload_from_df(stock_code=stock_code, df=df)


def _build_payload_from_df(stock_code: str, df: pd.DataFrame, bounds_df: pd.DataFrame | None = None) -> dict:
    """将行情 DataFrame 转换为前端图表 payload。"""
    if df is None or df.empty:
        raise RuntimeError('无法获取该时间段的股票日线数据')

    labels = []
    open_prices = []
    for _, row in df.iterrows():
        date_value = row['date']
        if hasattr(date_value, 'strftime'):
            labels.append(date_value.strftime('%Y-%m-%d'))
        else:
            labels.append(str(date_value))
        open_prices.append(float(row['open']))

    if bounds_df is None or bounds_df.empty:
        available_start = labels[0]
        available_end = labels[-1]
    else:
        bounds_labels = []
        for _, row in bounds_df.iterrows():
            date_value = row['date']
            if hasattr(date_value, 'strftime'):
                bounds_labels.append(date_value.strftime('%Y-%m-%d'))
            else:
                bounds_labels.append(str(date_value))
        available_start = bounds_labels[0]
        available_end = bounds_labels[-1]

    return {
        'stock_code': stock_code,
        'labels': labels,
        'open_prices': open_prices,
        'available_start': available_start,
        'available_end': available_end,
        'points': len(labels),
        'price_field': 'open',
    }


def _read_stock_cache_df(stock_code: str) -> pd.DataFrame | None:
    """读取单个股票缓存并标准化列。"""
    cache_file = os.path.join(_get_cache_dir(), f'{stock_code}.csv')
    if not os.path.exists(cache_file):
        return None

    try:
        df = pd.read_csv(cache_file, parse_dates=['date'])
    except Exception:
        return None

    required = ['date', 'open', 'high', 'low', 'close', 'volume']
    if not set(required).issubset(set(df.columns)):
        return None
    return df.loc[:, required].sort_values('date').reset_index(drop=True)


def _filter_df_by_optional_range(df: pd.DataFrame, start: str = '', end: str = '') -> pd.DataFrame:
    """按可选日期过滤缓存数据。"""
    out = df.copy()
    if start:
        out = out[out['date'] >= pd.to_datetime(start, format='%Y%m%d')]
    if end:
        out = out[out['date'] <= pd.to_datetime(end, format='%Y%m%d')]
    return out.sort_values('date').reset_index(drop=True)


def _restore_stock_cache(stock_code: str, cached_df: pd.DataFrame) -> None:
    """将指定股票缓存恢复到磁盘。"""
    cache_file = os.path.join(_get_cache_dir(), f'{stock_code}.csv')
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    cached_df.sort_values('date').to_csv(cache_file, index=False)


def _fetch_source_df(stock_code: str, start: str, end: str, source_name: str, temp_root: str) -> tuple[dict, pd.DataFrame | None]:
    """拉取单个数据源并返回日志和数据。"""
    started = time.time()
    source_cache_dir = os.path.join(temp_root, source_name)
    os.makedirs(source_cache_dir, exist_ok=True)
    try:
        df = stocks.get_data(
            symbol=stock_code,
            source=source_name,
            start_date=start or None,
            end_date=end or None,
            cache_dir=source_cache_dir,
            force_refresh=True,
            buffer_days=5,
        )
        if df is None or df.empty:
            raise RuntimeError('no data returned')

        duration_ms = int((time.time() - started) * 1000)
        return (
            {
                'source': source_name,
                'status': 'success',
                'rows': int(len(df)),
                'duration_ms': duration_ms,
                'message': f'下载成功，{len(df)} 条数据',
            },
            df,
        )
    except Exception as exc:
        duration_ms = int((time.time() - started) * 1000)
        return (
            {
                'source': source_name,
                'status': 'failed',
                'rows': 0,
                'duration_ms': duration_ms,
                'message': str(exc),
            },
            None,
        )


def _download_from_all_sources(stock_code: str, start: str, end: str) -> tuple[pd.DataFrame | None, list[dict]]:
    """并行拉取全部备选数据源，采用首个成功结果。"""
    logs_by_source: dict[str, dict] = {}
    first_success_df: pd.DataFrame | None = None
    first_success_source: str | None = None
    best_df: pd.DataFrame | None = None
    best_source: str | None = None
    best_rows: int = 0
    best_range: tuple[str, str] | None = None
    refreshed_by_later: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as temp_root:
        with ThreadPoolExecutor(max_workers=len(_DOWNLOAD_SOURCES)) as executor:
            future_map = {
                executor.submit(_fetch_source_df, stock_code, start, end, src, temp_root): src
                for src in _DOWNLOAD_SOURCES
            }
            for future in as_completed(future_map):
                source_name = future_map[future]
                try:
                    log_item, df = future.result()
                except Exception as exc:
                    log_item = {
                        'source': source_name,
                        'status': 'failed',
                        'rows': 0,
                        'duration_ms': 0,
                        'message': f'并行任务异常: {exc}',
                    }
                    df = None

                logs_by_source[source_name] = log_item
                if df is not None and not df.empty:
                    # 计算当前df的行数和时间范围
                    df_rows = len(df)
                    df_dates = pd.to_datetime(df['date'])
                    df_start = str(df_dates.min().date())
                    df_end = str(df_dates.max().date())
                    # 先到的直接采用
                    if first_success_df is None:
                        first_success_df = df.copy()
                        first_success_source = source_name
                        best_df = df.copy()
                        best_source = source_name
                        best_rows = df_rows
                        best_range = (df_start, df_end)
                        # 标记首个采用
                        logs_by_source[source_name]['status'] = 'success'
                        logs_by_source[source_name]['message'] += '（首个采用）'
                    else:
                        # 判断是否“更全”：行数更多，或时间范围更广
                        is_more_complete = False
                        # 行数更多
                        if df_rows > best_rows:
                            is_more_complete = True
                        # 时间范围更广
                        elif best_range is not None:
                            old_start, old_end = best_range
                            if df_start < old_start or df_end > old_end:
                                is_more_complete = True
                        if is_more_complete:
                            # 自动刷新缓存
                            best_df = df.copy()
                            best_source = source_name
                            best_rows = df_rows
                            best_range = (df_start, df_end)
                            refreshed_by_later[source_name] = True
                            logs_by_source[source_name] = {
                                **log_item,
                                'status': 'refreshed',
                                'message': f"后到数据更全，已刷新覆盖（覆盖 {first_success_source if first_success_source else ''}）",
                            }
                        else:
                            logs_by_source[source_name] = {
                                **log_item,
                                'status': 'discarded',
                                'message': f"较晚到达，已丢弃（采用 {best_source}）",
                            }

    ordered_logs = [logs_by_source.get(src, {
        'source': src,
        'status': 'failed',
        'rows': 0,
        'duration_ms': 0,
        'message': '未执行',
    }) for src in _DOWNLOAD_SOURCES]

    if best_df is None or best_df.empty:
        return None, ordered_logs

    best_df = best_df.copy()
    best_df['date'] = pd.to_datetime(best_df['date'])
    best_df = best_df.drop_duplicates(subset=['date'], keep='last').sort_values('date').reset_index(drop=True)

    cache_file = os.path.join(_get_cache_dir(), f'{stock_code}.csv')
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    best_df.to_csv(cache_file, index=False)
    return best_df, ordered_logs


def _build_fallback_payload(stock_code: str, start: str, end: str, cached_df: pd.DataFrame, error_text: str) -> dict:
    """在线失败时使用缓存构造降级 payload。"""
    ranged_df = _filter_df_by_optional_range(cached_df, start=start, end=end)
    used_full_cache_range = False
    if ranged_df.empty:
        ranged_df = cached_df.copy()
        used_full_cache_range = True

    payload = _build_payload_from_df(stock_code=stock_code, df=ranged_df, bounds_df=cached_df)
    payload['refreshed'] = False
    payload['degraded'] = True
    payload['used_full_cache_range'] = used_full_cache_range
    payload['warning'] = '在线下载失败，已自动降级为本地缓存数据。'
    payload['detail_error'] = str(error_text)
    payload['source_logs'] = []
    return payload


def _rebuild_chart_cache(stock_code: str, start: str = '', end: str = '', source: str = 'auto') -> None:
    """按当前请求区间强制重建当前股票缓存。"""
    stocks.get_data(
        symbol=stock_code,
        source=source,
        start_date=start or None,
        end_date=end or None,
        cache_dir=_get_cache_dir(),
        force_refresh=True,
        buffer_days=5,
    )


def _clear_all_cache_files() -> int:
    """清理 data 目录下所有 CSV 缓存文件。"""
    cache_dir = _get_cache_dir()
    if not os.path.isdir(cache_dir):
        return 0

    removed = 0
    for file_name in os.listdir(cache_dir):
        if not file_name.endswith('.csv'):
            continue
        file_path = os.path.join(cache_dir, file_name)
        if not os.path.isfile(file_path):
            continue
        os.remove(file_path)
        removed += 1

    return removed


def _collect_strategy_form_params(strategy_key: str) -> dict:
    """按策略注册表提取当前表单中的策略专属参数。"""
    params = {}
    spec = stocks.get_strategy_spec(strategy_key)
    for parameter in spec.parameters:
        raw_value = request.form.get(parameter.name, '')
        if raw_value != '':
            params[parameter.name] = raw_value
    return params


def _list_strategy_specs() -> list[stocks.StrategySpec]:
    """返回按 key 排序的策略列表，保证页面展示稳定。"""
    specs = stocks.list_strategy_specs()
    return sorted(specs, key=lambda item: item.key)


def _build_strategy_parameter_view(strategy_key: str) -> list[dict]:
    """构造策略参数在前端渲染所需的视图模型。"""
    spec = stocks.get_strategy_spec(strategy_key)
    items: list[dict] = []
    for parameter in spec.parameters:
        input_type = 'text'
        input_step = None
        if parameter.caster is int:
            input_type = 'number'
            input_step = '1'
        elif parameter.caster is float:
            input_type = 'number'
            input_step = '0.01'

        items.append(
            {
                'name': parameter.name,
                'label': parameter.label,
                'default': parameter.default,
                'description': parameter.description,
                'required': parameter.required,
                'input_type': input_type,
                'input_step': input_step,
            }
        )
    return items


def _render_strategy_selection(stock_code: str, stock_name: str):
    """渲染策略选择页（动态策略注册）。"""
    strategy_specs = _list_strategy_specs()
    return render_template(
        'select_strategy.html',
        stock_code=stock_code,
        stock_name=stock_name,
        strategy_specs=strategy_specs,
    )


def _lookup_stock_info(stock_code: str) -> dict[str, str]:
    """按股票代码返回展示信息。"""
    _init_stock_data()
    stock = _STOCK_INDEX.get(stock_code) if _STOCK_INDEX else None
    if isinstance(stock, dict):
        return {'code': stock['code'], 'name': stock['name']}
    return {'code': stock_code, 'name': '缓存股票'}


def _list_cached_stocks() -> list[dict[str, str]]:
    """列出 data 目录下所有有缓存的股票。"""
    cache_dir = _get_cache_dir()
    if not os.path.isdir(cache_dir):
        return []

    items: list[dict[str, str]] = []
    for file_name in sorted(os.listdir(cache_dir)):
        if not file_name.endswith('.csv'):
            continue
        stock_code = file_name[:-4]
        items.append(_lookup_stock_info(stock_code))
    return items


def _list_recent_stocks() -> list[dict[str, str]]:
    """读取会话中的最近选择历史。"""
    recent_codes = session.get('recent_stock_codes', [])
    if not isinstance(recent_codes, list):
        return []
    return [_lookup_stock_info(stock_code) for stock_code in recent_codes]


def _render_stock_selection():
    """渲染股票选择页。"""
    return render_template(
        'select_stock.html',
        recent_stocks=_list_recent_stocks(),
        cached_stocks=_list_cached_stocks(),
    )


def _push_recent_stock(code: str) -> None:
    """将股票加入最近使用记录。"""
    recent_codes = session.get('recent_stock_codes', [])
    if not isinstance(recent_codes, list):
        recent_codes = []
    recent_codes = [code] + [item for item in recent_codes if item != code]
    session['recent_stock_codes'] = recent_codes[:20]

def _init_stock_data():
    """初始化股票数据和索引"""
    global _STOCK_LIST, _STOCK_INDEX
    if _STOCK_LIST is None:
        stock_file = os.path.join(os.path.dirname(__file__), 'stock_list.json')
        with open(stock_file, 'r', encoding='utf-8') as f:
            _STOCK_LIST = json.load(f)

        # 创建索引以支持O(1)查找
        _STOCK_INDEX = {}
        for stock in _STOCK_LIST:
            _STOCK_INDEX[stock['code']] = stock
            _STOCK_INDEX[stock['name']] = stock

def get_stock_list():
    """获取股票列表"""
    _init_stock_data()
    return _STOCK_LIST

def search_stock_by_query(query: str):
    """通过代码或名称搜索标的。

    返回匹配结果列表（可能为空）。实现策略：
    - 优先精确匹配代码或名称（若存在，则返回该项为唯一结果）
    - 否则进行模糊匹配，返回所有包含查询字符串的项目列表
    """
    _init_stock_data()
    results = []
    # 先尝试精确匹配（代码或名称）
    exact = _STOCK_INDEX.get(query)
    if exact:
        return [exact]

    query_lower = query.lower()
    for stock in _STOCK_LIST:
        code = str(stock.get('code', ''))
        name = str(stock.get('name', ''))
        if query in code or query_lower in name.lower():
            results.append(stock)

    return results


@app.route('/', methods=['GET'])
def index():
    """首页：股票选择"""
    return _render_stock_selection()


@app.route('/strategies', methods=['GET'])
def strategies_index():
    """策略列表首页 — 由注册表驱动的 Jinja2 循环渲染"""
    specs = _list_strategy_specs()
    return render_template('index.html', strategy_specs=specs)


@app.route('/api/search_stock', methods=['GET'])
def search_stock():
    """搜索股票API"""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': '请输入股票代码或名称'})

    # 使用优化后的索引查找
    matches = search_stock_by_query(query)
    if not matches:
        return jsonify({'error': f'未找到股票：{query}。请检查股票代码或名称是否正确。'})

    # 若只有一项匹配，保持向后兼容：返回单个对象（code/name）
    if len(matches) == 1:
        stock = matches[0]
        return jsonify({'code': stock['code'], 'name': stock['name']})

    # 多项时返回 results 数组，供前端选择
    simplified = [{'code': s['code'], 'name': s['name']} for s in matches]
    return jsonify({'results': simplified})


@app.route('/api/stock_price/<stock_code>', methods=['GET'])
def get_stock_price(stock_code):
    """获取股票最新价格API

    返回股票的最新收盘价，用于实时计算每手金额和可购买手数。
    使用缓存数据的最新价格，避免频繁请求外部数据源。
    """
    try:
        # 从缓存获取股票数据（仅获取最近一条数据以提高性能）
        df = stocks.get_data(symbol=stock_code, source='auto', cache_dir=_get_cache_dir())

        if df is None or df.empty:
            return jsonify({'error': '无法获取股票数据'}), 404

        # 获取最新一条数据的收盘价
        latest_data = df.iloc[-1]
        latest_price = float(latest_data['close'])
        latest_date = str(latest_data['date'].date()) if hasattr(latest_data['date'], 'date') else str(latest_data['date'])

        return jsonify({
            'price': latest_price,
            'date': latest_date,
            'stock_code': stock_code
        })

    except Exception as e:
        return jsonify({'error': f'获取价格失败: {str(e)}'}), 500


@app.route('/api/select_stock', methods=['POST'])
def select_stock():
    """选择股票API"""
    data = request.get_json()
    code = data.get('code')
    name = data.get('name')

    if not code or not name:
        return jsonify({'success': False, 'error': '股票代码和名称不能为空'})

    # 保存到session
    session['stock_code'] = code
    session['stock_name'] = name
    _push_recent_stock(code)

    return jsonify({'success': True})


@app.route('/api/select_strategy', methods=['POST'])
def select_strategy_api():
    """选择策略API"""
    data = request.get_json()
    strategy_type = data.get('strategy_type')
    strategy_name = data.get('strategy_name')

    if not strategy_type or not strategy_name:
        return jsonify({'success': False, 'error': '策略类型和名称不能为空'})

    # 保存到session
    session['strategy_type'] = strategy_type
    session['strategy_name'] = strategy_name

    return jsonify({'success': True})


@app.route('/api/select_multi_strategies', methods=['POST'])
def select_multi_strategies_api():
    """多策略对比 — 保存选中的策略列表到session"""
    data = request.get_json()
    strategies = data.get('strategies', [])
    strategy_names = data.get('strategy_names', [])

    if not strategies or len(strategies) < 2:
        return jsonify({'success': False, 'error': '请至少选择 2 个策略'})

    session['multi_strategies'] = strategies
    session['multi_strategy_names'] = strategy_names
    session['strategy_type'] = strategies[0]  # fallback
    session['strategy_name'] = strategy_names[0] if strategy_names else strategies[0]

    return jsonify({'success': True})


@app.route('/select_strategies_multi', methods=['GET'])
def select_strategies_multi():
    """多策略选择页面 — 勾选多个策略"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')

    if not stock_code or not stock_name:
        return _render_stock_selection()

    strategy_specs = _list_strategy_specs()
    return render_template(
        'select_strategies_multi.html',
        stock_code=stock_code,
        stock_name=stock_name,
        strategy_specs=strategy_specs,
    )


@app.route('/select_strategy', methods=['GET'])
def select_strategy():
    """策略选择页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')

    if not stock_code or not stock_name:
        # 如果没有选择股票，跳转回首页
        return _render_stock_selection()

    return _render_strategy_selection(stock_code=stock_code, stock_name=stock_name)


@app.route('/select_mode', methods=['GET'])
def select_mode():
    """运行模式选择页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    strategy_type = session.get('strategy_type')
    strategy_name = session.get('strategy_name')

    if not stock_code or not stock_name or not strategy_type or not strategy_name:
        # 如果缺少必要信息，跳转回相应页面
        if not stock_code or not stock_name:
            return _render_stock_selection()
        return _render_strategy_selection(stock_code=stock_code, stock_name=stock_name)

    return render_template('select_mode.html',
                         stock_code=stock_code,
                         stock_name=stock_name,
                         strategy_type=strategy_type,
                         strategy_name=strategy_name)


@app.route('/api/select_mode', methods=['POST'])
def select_mode_api():
    """选择运行模式API"""
    data = request.get_json()
    mode = data.get('mode')

    if not mode:
        return jsonify({'success': False, 'error': '运行模式不能为空'})

    # 保存到session
    session['run_mode'] = mode

    return jsonify({'success': True})


@app.route('/select_time_range', methods=['GET'])
def select_time_range():
    """回测时间段设置页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    strategy_type = session.get('strategy_type')
    strategy_name = session.get('strategy_name')
    run_mode = session.get('run_mode')

    if not stock_code or not stock_name or not strategy_type or not strategy_name:
        # 如果缺少必要信息，跳转回相应页面
        if not stock_code or not stock_name:
            return _render_stock_selection()
        return _render_strategy_selection(stock_code=stock_code, stock_name=stock_name)

    if not run_mode or run_mode != 'backtest':
        # 只有回测模式需要设置时间段
        return render_template('select_mode.html',
                             stock_code=stock_code,
                             stock_name=stock_name,
                             strategy_type=strategy_type,
                             strategy_name=strategy_name)

    return render_template('select_time_range.html',
                         stock_code=stock_code,
                         stock_name=stock_name,
                         strategy_type=strategy_type,
                         strategy_name=strategy_name)


@app.route('/api/select_time_range', methods=['POST'])
def select_time_range_api():
    """保存回测时间段API"""
    data = request.get_json()
    if data is None:
        return jsonify({'success': False, 'error': '请求体必须是JSON格式'}), 400

    start = data.get('start', '')
    end = data.get('end', '')

    # 后端验证：start和end必须为空或符合YYYYMMDD格式
    import re
    date_pattern = re.compile(r'^\d{8}$')

    if start and not date_pattern.match(start):
        return jsonify({'success': False, 'error': '起始日期格式必须为YYYYMMDD'}), 400
    if end and not date_pattern.match(end):
        return jsonify({'success': False, 'error': '结束日期格式必须为YYYYMMDD'}), 400

    # 验证start <= end
    if start and end and start > end:
        return jsonify({'success': False, 'error': '起始日期不能晚于结束日期'}), 400

    # 保存到session（可以为空字符串，表示使用全部数据）
    session['backtest_start'] = start
    session['backtest_end'] = end

    return jsonify({'success': True})


@app.route('/api/stock_chart/<stock_code>', methods=['GET'])
def get_stock_chart(stock_code):
    """获取时间段页面的股票日线开盘价走势图数据。"""
    session_stock_code = session.get('stock_code')
    if not session_stock_code:
        return jsonify({'error': '请先选择股票'}), 400
    if session_stock_code != stock_code:
        return jsonify({'error': '当前股票与会话不一致'}), 400

    try:
        start, end = _validate_optional_date_range(
            request.args.get('start', ''),
            request.args.get('end', ''),
        )
        payload = _build_stock_chart_payload(stock_code=stock_code, start=start, end=end)
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'获取走势图失败: {str(exc)}'}), 500


@app.route('/api/stock_chart/<stock_code>/refresh_cache', methods=['POST'])
def refresh_stock_chart_cache(stock_code):
    """清除全部缓存并重新下载当前股票的日线数据。"""
    session_stock_code = session.get('stock_code')
    if not session_stock_code:
        return jsonify({'error': '请先选择股票'}), 400
    if session_stock_code != stock_code:
        return jsonify({'error': '当前股票与会话不一致'}), 400

    data = request.get_json(silent=True) or {}

    start = ''
    end = ''
    removed_files = 0
    cached_before_refresh = None

    try:
        start, end = _validate_optional_date_range(
            data.get('start', ''),
            data.get('end', ''),
        )
        cached_before_refresh = _read_stock_cache_df(stock_code)
        removed_files = _clear_all_cache_files()
        merged_df, source_logs = _download_from_all_sources(stock_code=stock_code, start=start, end=end)
        if merged_df is None or merged_df.empty:
            raise RuntimeError('全部备选数据源下载失败')

        ranged_df = _filter_df_by_optional_range(merged_df, start=start, end=end)
        if ranged_df.empty:
            ranged_df = merged_df

        payload = _build_payload_from_df(stock_code=stock_code, df=ranged_df, bounds_df=merged_df)
        payload['removed_cache_files'] = removed_files
        payload['refreshed'] = True
        payload['degraded'] = False
        payload['source_logs'] = source_logs
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        if cached_before_refresh is not None and not cached_before_refresh.empty:
            try:
                _restore_stock_cache(stock_code=stock_code, cached_df=cached_before_refresh)
                payload = _build_fallback_payload(
                    stock_code=stock_code,
                    start=start,
                    end=end,
                    cached_df=cached_before_refresh,
                    error_text=str(exc),
                )
                payload['removed_cache_files'] = removed_files
                payload['source_logs'] = payload.get('source_logs', [])
                return jsonify(payload)
            except Exception:
                pass
        return jsonify({'error': f'清除缓存并重新下载失败: {str(exc)}'}), 500


@app.route('/strategy/<strategy_key>', methods=['GET'])
def strategy_config(strategy_key: str):
    """通用策略配置页面 — 所有策略共用单一路由。"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    strategy_type = session.get('strategy_type')
    run_mode = session.get('run_mode')

    if not stock_code or not stock_name:
        return _render_stock_selection()
    if not strategy_type:
        return _render_strategy_selection(stock_code=stock_code, stock_name=stock_name)
    if not run_mode:
        return render_template(
            'select_mode.html',
            stock_code=stock_code,
            stock_name=stock_name,
            strategy_type=strategy_type,
            strategy_name=session.get('strategy_name', strategy_key),
        )

    try:
        spec = stocks.get_strategy_spec(strategy_key)
    except Exception:
        return _render_strategy_selection(stock_code=stock_code, stock_name=stock_name)

    return render_template(
        spec.template,
        stock_code=stock_code,
        stock_name=stock_name,
        strategy_key=spec.key,
        strategy_label=spec.label,
        strategy_description=spec.description,
        parameters=_build_strategy_parameter_view(strategy_key=spec.key),
    )


@app.route('/run', methods=['POST'])
def run():
    # 从session获取股票信息和时间段
    symbol = session.get('stock_code')
    if not symbol:
        # 如果session中没有股票信息，回退到从表单获取（向后兼容）
        symbol = request.form.get('symbol', '600900').strip()

    # 时间段取值优先级：表单显式传的非空值 > session 中的值 > None
    form_start = request.form.get('start', '').strip()
    form_end = request.form.get('end', '').strip()

    if form_start:
        start = form_start if form_start else None
    else:
        start = session.get('backtest_start') or None

    if form_end:
        end = form_end if form_end else None
    else:
        end = session.get('backtest_end') or None

    source = request.form.get('source', 'auto')
    strategy = request.form.get('strategy', 'sma')
    lot = float(request.form.get('lot') or 100.0)
    cash = float(request.form.get('cash') or 100000.0)
    strategy_params = _collect_strategy_form_params(strategy)
    request_payload = {
        'symbol': symbol,
        'strategy': strategy,
        'source': source,
        'start_date': start,
        'end_date': end,
        'lot_size': lot,
        'init_cash': cash,
        'trade_price': stocks.TRADE_PRICE_OPEN,
        'strategy_params': strategy_params,
    }

    # 创建回测任务
    progress_mgr = get_progress_manager()
    task_id = progress_mgr.create_task()

    # 创建进度回调函数
    def progress_callback(current, total):
        progress_mgr.update_progress(task_id, current, total)

    # 在后台线程执行回测
    def run_backtest():
        try:
            backtest_request = stocks.create_backtest_request(
                progress_callback=progress_callback,
                **request_payload,
            )
            res = stocks.run_backtest(backtest_request)

            if progress_mgr.is_cancelled(task_id):
                return

            # 设置任务结果
            progress_mgr.set_result(task_id, res)

        except Exception as e:
            # 设置任务错误
            progress_mgr.set_error(task_id, str(e))

    if app.testing:
        run_backtest()
    else:
        # 启动后台线程
        thread = threading.Thread(target=run_backtest, daemon=True)
        thread.start()

    # 返回进度页面
    strategy_spec = stocks.get_strategy_spec(strategy)
    return render_template(
        'backtest_progress.html',
        task_id=task_id,
        symbol=symbol,
        strategy=strategy,
        strategy_label=strategy_spec.label,
        back_url=f'/strategy/{strategy}',
    )


@app.route('/api/progress/<task_id>')
def progress_stream(task_id):
    """SSE端点：推送回测进度"""
    progress_mgr = get_progress_manager()

    def generate():
        for event in progress_mgr.get_events(task_id):
            yield f"data: {json.dumps(event)}\n\n"

        # 清理任务数据（延迟清理，确保客户端能接收到最后的消息）
        import time
        time.sleep(1)
        progress_mgr.cleanup_task(task_id)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/progress/<task_id>/cancel', methods=['POST'])
def cancel_progress(task_id):
    """用户放弃等待当前回测。"""
    progress_mgr = get_progress_manager()
    task = progress_mgr.get_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    progress_mgr.cancel_task(task_id)
    return jsonify({'success': True})


@app.route('/api/result/<task_id>')
def get_result(task_id):
    """获取回测结果"""
    progress_mgr = get_progress_manager()
    task = progress_mgr.get_task(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if task['status'] == 'error':
        return jsonify({'error': task['error']}), 500

    if task['status'] == 'cancelled':
        return jsonify({'error': '任务已取消'}), 410

    if task['status'] != 'completed':
        return jsonify({'error': '任务未完成'}), 400

    return jsonify({'result': task['result']})


@app.route('/view_result', methods=['POST'])
def view_result():
    """查看回测结果 — 统一使用通用模板"""
    result_json = request.form.get('result_json')
    if not result_json:
        return render_template('result_generic.html', error='无法获取回测结果')

    try:
        res = json.loads(result_json)
        if isinstance(res, dict):
            strategy_name = session.get('strategy_name', '')
            return render_template('result_generic.html', result=res, strategy_name=strategy_name)
        else:
            return render_template('result_generic.html', error='回测结果格式不正确')
    except Exception as e:
        return render_template('result_generic.html', error=f'解析结果失败: {e}')


@app.route('/run_multi', methods=['POST'])
def run_multi():
    """多策略对比回测入口"""
    symbol = session.get('stock_code')
    if not symbol:
        symbol = request.form.get('symbol', '600900').strip()

    strategies = session.get('multi_strategies', [])
    strategy_names = session.get('multi_strategy_names', [])

    if not strategies or len(strategies) < 2:
        return render_template('result_compare.html',
                               error='请至少选择 2 个策略进行对比',
                               strategy_names=[],
                               results=[])

    form_start = request.form.get('start', '').strip()
    form_end = request.form.get('end', '').strip()

    start = form_start if form_start else (session.get('backtest_start') or None)
    end = form_end if form_end else (session.get('backtest_end') or None)

    source = request.form.get('source', 'auto')
    lot = float(request.form.get('lot') or 100.0)
    cash = float(request.form.get('cash') or 100000.0)

    progress_mgr = get_progress_manager()
    task_id = progress_mgr.create_task()

    def progress_callback(current, total):
        progress_mgr.update_progress(task_id, current, total)

    def run_multi_backtest():
        try:
            res = stocks.run_multi_strategy_backtest(
                symbol=symbol,
                source=source,
                start_date=start,
                end_date=end,
                lot_size=lot,
                init_cash=cash,
                trade_price=stocks.TRADE_PRICE_OPEN,
                strategies=strategies,
                progress_callback=progress_callback,
            )

            if progress_mgr.is_cancelled(task_id):
                return

            progress_mgr.set_result(task_id, res)

        except Exception as e:
            progress_mgr.set_error(task_id, str(e))

    if app.testing:
        run_multi_backtest()
    else:
        thread = threading.Thread(target=run_multi_backtest, daemon=True)
        thread.start()

    return render_template(
        'backtest_progress.html',
        task_id=task_id,
        symbol=symbol,
        strategy='multi',
        strategy_label='多策略对比',
        back_url='/select_strategies_multi',
        result_url='/view_result_compare',
    )


@app.route('/view_result_compare', methods=['POST'])
def view_result_compare():
    """多策略对比结果页面"""
    result_json = request.form.get('result_json')
    if not result_json:
        return render_template('result_compare.html',
                               error='无法获取回测结果',
                               strategy_names=[],
                               results=[])

    try:
        res = json.loads(result_json)
        strategies = res.get('strategies', [])
        strategy_names = [s.get('strategy_label', s.get('strategy_key', '未知')) for s in strategies]

        # 过滤掉有错误的策略
        valid_results = [s for s in strategies if 'error' not in s]

        # 计算最优指标（用于高亮）
        best_return = max(
            [s.get('metrics', {}).get('total_return_rate', -999) for s in valid_results],
            default=-999
        )
        best_sharpe = max(
            [s.get('metrics', {}).get('sharpe_ratio', -999) for s in valid_results],
            default=-999
        )
        best_drawdown = min(
            [s.get('metrics', {}).get('max_drawdown', 999) for s in valid_results],
            default=999
        )

        return render_template(
            'result_compare.html',
            results=valid_results,
            strategy_names=strategy_names,
            symbol=res.get('symbol', ''),
            start_date=res.get('start_date', ''),
            end_date=res.get('end_date', ''),
            best_return=best_return,
            best_sharpe=best_sharpe,
            best_drawdown=best_drawdown,
            error=None,
        )
    except Exception as e:
        return render_template('result_compare.html',
                               error=f'解析结果失败: {e}',
                               strategy_names=[],
                               results=[])


@app.route('/download/excel', methods=['POST'])
def download_excel():
    # 导出回测结果为 Excel 文件。
    result_json = request.form.get('result_json')
    if not result_json:
        return jsonify({'error': '无法获取回测结果'}), 400

    try:
        res = json.loads(result_json)
    except json.JSONDecodeError:
        return jsonify({'error': '结果数据格式错误'}), 400

    if not isinstance(res, dict):
        return jsonify({'error': '结果数据格式错误'}), 400

    try:
        strategy_name = request.form.get('strategy_name', '')
        symbol = res.get('symbol', 'UNKNOWN')
        start_date = res.get('start_date', '')
        end_date = res.get('end_date', '')

        fname = generate_filename(symbol, strategy_name, start_date, end_date, 'xlsx')

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            output_path = export_to_excel(
                backtest_result=res,
                output_path=tmp.name,
                strategy_name=strategy_name,
            )

        with open(output_path, 'rb') as f:
            data = f.read()
        os.unlink(output_path)

        response = app.response_class(
            response=data,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response
    except Exception as e:
        return jsonify({'error': f'导出 Excel 失败: {str(e)}'}), 500


@app.route('/download/pdf', methods=['POST'])
def download_pdf():
    # 导出回测结果为 PDF 文件。
    result_json = request.form.get('result_json')
    if not result_json:
        return jsonify({'error': '无法获取回测结果'}), 400

    try:
        res = json.loads(result_json)
    except json.JSONDecodeError:
        return jsonify({'error': '结果数据格式错误'}), 400

    if not isinstance(res, dict):
        return jsonify({'error': '结果数据格式错误'}), 400

    try:
        strategy_name = request.form.get('strategy_name', '')
        symbol = res.get('symbol', 'UNKNOWN')
        start_date = res.get('start_date', '')
        end_date = res.get('end_date', '')

        fname = generate_filename(symbol, strategy_name, start_date, end_date, 'pdf')
        pdf_data = prepare_pdf_data(res, strategy_name)

        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()

        # Register a Unicode font for Chinese character support via fontconfig
        def _find_cjk_font():
            import subprocess
            try:
                result = subprocess.run(
                    ['fc-match', '-f', '%{file}', 'wqy-zenhei,Noto Sans CJK SC,SimHei,Microsoft YaHei,Droid Sans Fallback'],
                    capture_output=True, text=True, timeout=5
                )
                path = result.stdout.strip()
                if path and os.path.exists(path):
                    return path
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            # fallback: scan known directories
            for d in ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts')]:
                for root, _dirs, files in os.walk(d):
                    for f in files:
                        if f.endswith(('.ttc', '.ttf')) and any(k in f.lower() for k in ['wqy', 'noto', 'simhei', 'yahei', 'droid']):
                            return os.path.join(root, f)
            return None

        _CJK_FONT_PATH = _find_cjk_font()
        if _CJK_FONT_PATH:
            pdf.add_font('CJK', '', _CJK_FONT_PATH)
            font_body = 'CJK'
            font_body_bold = 'CJK'
        else:
            font_body = 'Helvetica'
            font_body_bold = 'Helvetica'

        pdf.set_font(font_body_bold, '', 16)
        pdf.cell(0, 12, 'Backtest Report', new_x='LMARGIN', new_y='NEXT', align='C')
        pdf.ln(4)

        pdf.set_font(font_body_bold, '', 12)
        pdf.cell(0, 8, 'Summary Information', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font(font_body, '', 10)
        summary = pdf_data['summary']
        for k, v in [('Symbol', summary['symbol']),
                     ('Strategy', summary['strategy_name']),
                     ('Start Date', summary['start_date']),
                     ('End Date', summary['end_date']),
                     ('Initial Capital', f"${summary['init_cash']:,.2f}")]:
            pdf.cell(50, 6, k + ':', border=0)
            pdf.cell(0, 6, str(v), new_x='LMARGIN', new_y='NEXT')
        pdf.ln(4)

        pdf.set_font(font_body_bold, '', 12)
        pdf.cell(0, 8, 'Key Metrics', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font(font_body, '', 10)
        metrics = pdf_data['metrics']
        for k, v in [('Total Return Rate', f"{metrics['total_return_rate']*100:.2f}%"),
                     ('Annualized Return', f"{metrics['annualized_return']*100:.2f}%"),
                     ('Max Drawdown', f"{metrics['max_drawdown']*100:.2f}%"),
                     ('Sharpe Ratio', f"{metrics['sharpe_ratio']:.4f}"),
                     ('Total P/L', f"${metrics['total_pl']:,.2f}"),
                     ('Final Value', f"${metrics['final_value']:,.2f}")]:
            pdf.cell(50, 6, k + ':', border=0)
            pdf.cell(0, 6, str(v), new_x='LMARGIN', new_y='NEXT')
        pdf.ln(4)

        pdf.set_font(font_body_bold, '', 12)
        pdf.cell(0, 8, 'Trade Records', new_x='LMARGIN', new_y='NEXT')

        trades = pdf_data['trades']
        col_widths = [30, 20, 25, 20, 25]
        headers = ['Date', 'Action', 'Price', 'Shares', 'P/L']

        pdf.set_font(font_body_bold, '', 8)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 7, h, border=1, align='C')
        pdf.ln()

        pdf.set_font(font_body, '', 8)
        max_rows = min(len(trades), 50)
        for t in trades[:max_rows]:
            pdf.cell(col_widths[0], 6, str(t.get('date', '')), border=1)
            pdf.cell(col_widths[1], 6, str(t.get('action', '')), border=1, align='C')
            pdf.cell(col_widths[2], 6, f"{t.get('price', 0):.2f}", border=1, align='R')
            pdf.cell(col_widths[3], 6, str(t.get('shares', 0)), border=1, align='R')
            pl = t.get('pl', '')
            pl_str = f"{pl:.2f}" if isinstance(pl, (int, float)) else str(pl)
            pdf.cell(col_widths[4], 6, pl_str, border=1, align='R')
            pdf.ln()

        if len(trades) > 50:
            pdf.set_font(font_body, 'I', 8)
            pdf.cell(0, 6, f'(Showing first 50 of {len(trades)} trades)', new_x='LMARGIN', new_y='NEXT')

        pdf_bytes = pdf.output()
        response = app.response_class(
            response=pdf_bytes,
            mimetype='application/pdf',
        )
        response.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response
    except Exception as e:
        return jsonify({'error': f'导出 PDF 失败: {str(e)}'}), 500

# ── 模拟盘交易 (Paper Trading) ───────────────────────────

try:
    from trader.papertrade import engine as _paper_engine
    HAS_PAPER_ENGINE = True
except (ImportError, AttributeError):
    _paper_engine = None
    HAS_PAPER_ENGINE = False


def _get_paper_engine():
    """Return the paper trade engine singleton, or None if unavailable."""
    global _paper_engine, HAS_PAPER_ENGINE
    if _paper_engine is None:
        try:
            from trader.papertrade import engine as e
            _paper_engine = e
            HAS_PAPER_ENGINE = True
            return _paper_engine
        except (ImportError, AttributeError):
            return None
    return _paper_engine


@app.route('/papertrade')
def papertrade():
    """模拟盘仪表盘页面"""
    engine = _get_paper_engine()
    status = {}
    if engine:
        try:
            status = engine.get_status()
        except Exception:
            status = {'status': 'stopped'}
    return render_template('papertrade.html', status=status)


@app.route('/papertrade/setup', methods=['GET', 'POST'])
def papertrade_setup():
    """模拟盘配置页面"""
    if request.method == 'POST':
        # Handle form-based POST (redirect approach)
        return papertrade_start()
    return render_template('papertrade_setup.html')


@app.route('/papertrade/start', methods=['POST'])
def papertrade_start():
    """启动模拟盘"""
    engine = _get_paper_engine()
    if engine is None:
        return jsonify({'success': False, 'error': '模拟盘引擎未加载，请先构建 trader.papertrade 模块'}), 503

    data = request.get_json(silent=True) or {}
    try:
        engine.configure(
            strategy_key=data.get('strategy_key', 'sma'),
            stock_code=data.get('stock_code', '600900'),
            params=data.get('params', {}),
            init_cash=float(data.get('init_cash', 100000)),
            lot_size=float(data.get('lot_size', 100)),
            source=data.get('source', 'auto'),
            interval_seconds=int(data.get('interval_seconds', 300)),
        )
        ok = engine.start()
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/papertrade/stop', methods=['POST'])
def papertrade_stop():
    """停止模拟盘"""
    engine = _get_paper_engine()
    if engine is None:
        return jsonify({'success': False, 'error': '模拟盘引擎未加载'}), 503
    try:
        ok = engine.stop()
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/papertrade/status')
def papertrade_status():
    """获取模拟盘状态 (JSON)"""
    engine = _get_paper_engine()
    if engine is None:
        return jsonify({'status': 'stopped', 'error': '引擎未加载'})
    try:
        return jsonify(engine.get_status())
    except Exception as e:
        return jsonify({'status': 'stopped', 'error': str(e)})


@app.route('/papertrade/trades')
def papertrade_trades():
    """获取交易记录列表 (JSON)"""
    engine = _get_paper_engine()
    if engine is None:
        return jsonify({'trades': [], 'error': '引擎未加载'})
    try:
        limit = request.args.get('limit', 50, type=int)
        return jsonify(engine.get_trades(limit=limit))
    except Exception as e:
        return jsonify({'trades': [], 'error': str(e)})


# ── 参数预设 API ─────────────────────────────────────────

@app.route('/save_preset', methods=['POST'])
def save_preset_route():
    """保存参数预设。"""
    data = request.get_json()
    if not data or not data.get('name') or not data.get('strategy_key'):
        return jsonify({'error': '缺少必填字段: name, strategy_key'}), 400
    try:
        persistence.save_preset(
            name=data['name'],
            strategy_key=data['strategy_key'],
            params=data.get('params'),
            source=data.get('source'),
            lot_size=data.get('lot'),
            init_cash=data.get('cash'),
            stock_code=data.get('stock'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            trade_price=data.get('trade_price'),
        )
        saved_name = data['name']
        return jsonify({'success': True, 'message': f'预设「{saved_name}」保存成功'})
    except Exception as e:
        return jsonify({'error': f'保存预设失败: {str(e)}'}), 500


@app.route('/load_preset/<name>', methods=['GET'])
def load_preset_route(name: str):
    """加载指定名称的预设。"""
    preset = persistence.load_preset_by_name(name)
    if preset is None:
        return jsonify({'error': f'预设「{name}」不存在'}), 404
    return jsonify(preset)


@app.route('/list_presets', methods=['GET'])
def list_presets_route():
    """列出所有预设。"""
    strategy_key = request.args.get('strategy_key')
    presets = persistence.list_presets(strategy_key=strategy_key)
    return jsonify(presets)


@app.route('/delete_preset/<name>', methods=['DELETE'])
def delete_preset_route(name: str):
    """删除指定预设。"""
    try:
        persistence.delete_preset(name)
        return jsonify({'success': True, 'message': f'预设「{name}」已删除'})
    except Exception as e:
        return jsonify({'error': f'删除预设失败: {str(e)}'}), 500


@app.route('/api/presets_for_strategy/<strategy_key>', methods=['GET'])
def presets_for_strategy_route(strategy_key: str):
    """返回指定策略的预设列表。"""
    presets = persistence.list_presets(strategy_key=strategy_key)
    return jsonify(presets)


# ── 回测结果历史 API ────────────────────────────────────

@app.route('/save_result_history', methods=['POST'])
def save_result_history_route():
    """保存回测结果到历史记录。"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    result = data.get('result', {})
    req = data.get('request_params', {})

    strategy_key = req.get('strategy', result.get('strategy', ''))
    stock_code = req.get('symbol', result.get('symbol', ''))
    stock_name = data.get('stock_name', '')
    start_date = req.get('start_date', result.get('start_date', ''))
    end_date = req.get('end_date', result.get('end_date', ''))

    params = req.get('strategy_params', {})
    metrics = result.get('metrics', {})
    trades_count = result.get('trades', 0) or len(result.get('trades_list', []))
    total_returns = metrics.get('total_return_rate', 0.0)
    sharp_ratio = metrics.get('sharpe_ratio', 0.0)
    max_drawdown = metrics.get('max_drawdown', 0.0)
    preset_name = data.get('preset_name')

    try:
        result_id = persistence.save_result(
            strategy_key=strategy_key,
            stock_code=stock_code,
            stock_name=stock_name,
            start_date=start_date,
            end_date=end_date,
            params=params,
            metrics=metrics,
            trades_count=trades_count,
            total_returns=total_returns,
            sharp_ratio=sharp_ratio,
            max_drawdown=max_drawdown,
            preset_name=preset_name,
        )
        return jsonify({'success': True, 'result_id': result_id})
    except Exception as e:
        return jsonify({'error': f'保存历史记录失败: {str(e)}'}), 500


@app.route('/history', methods=['GET'])
def history_route():
    """历史回测结果列表页。"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    results, total = persistence.list_results(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return render_template(
        'history.html',
        results=results,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@app.route('/result/<int:result_id>', methods=['GET'])
def result_detail_route(result_id: int):
    """查看历史回测结果详情。"""
    row = persistence.get_result(result_id)
    if row is None:
        return render_template('result_generic.html', error=f'结果记录 #{result_id} 不存在')

    # 将数据库行重建为 result_generic.html 所需的完整 result dict
    result = {
        'symbol': row.get('stock_code', ''),
        'stock_code': row.get('stock_code', ''),
        'stock_name': row.get('stock_name', ''),
        'start_date': row.get('start_date', ''),
        'end_date': row.get('end_date', ''),
        'metrics': row.get('metrics', {}),
        'trades': row.get('trades_count', 0),
        'trades_list': [],
        'history': [],
        'init_cash': None,
        'total_value': None,
        'cash': None,
        'shares': None,
        'last_price': None,
        'market_value': None,
        'realized_pl': None,
        'unrealized_pl': None,
    }
    strategy_name = row.get('strategy_key', '')
    return render_template('result_generic.html', result=result, strategy_name=strategy_name)


if __name__ == '__main__':
    # 支持通过环境变量自定义主机和端口，方便测试使用非默认端口
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5001'))
    debug = os.environ.get('FLASK_ENV', '') != 'production'
    app.run(host=host, port=port, debug=debug)
