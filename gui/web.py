import os
import sys
import json
import threading
from flask import Flask, render_template, request, session, jsonify, Response

# Ensure project root is on sys.path so sibling packages (e.g. `source`) can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import stocks
from gui.backtest_progress import get_progress_manager

app = Flask(__name__, template_folder='templates')
# 使用环境变量配置secret_key，开发环境使用默认值
app.secret_key = os.environ.get('SECRET_KEY', 'stocks-quantitative-backtest-secret-key-2024')

# 在应用启动时加载股票列表到内存，避免重复文件IO
_STOCK_LIST = None
_STOCK_INDEX = None

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
    """通过代码或名称搜索股票（精确匹配）"""
    _init_stock_data()
    return _STOCK_INDEX.get(query)


@app.route('/', methods=['GET'])
def index():
    """首页：股票选择"""
    return render_template('select_stock.html')


@app.route('/api/search_stock', methods=['GET'])
def search_stock():
    """搜索股票API"""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': '请输入股票代码或名称'})

    # 使用优化后的索引查找
    stock = search_stock_by_query(query)
    if stock:
        return jsonify({'code': stock['code'], 'name': stock['name']})

    return jsonify({'error': f'未找到股票：{query}。请检查股票代码或名称是否正确。'})


@app.route('/api/stock_price/<stock_code>', methods=['GET'])
def get_stock_price(stock_code):
    """获取股票最新价格API

    返回股票的最新收盘价，用于实时计算每手金额和可购买手数。
    使用缓存数据的最新价格，避免频繁请求外部数据源。
    """
    try:
        # 从缓存获取股票数据（仅获取最近一条数据以提高性能）
        df = stocks.get_data(symbol=stock_code, source='auto', cache_dir='data')

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


@app.route('/select_strategy', methods=['GET'])
def select_strategy():
    """策略选择页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')

    if not stock_code or not stock_name:
        # 如果没有选择股票，跳转回首页
        return render_template('select_stock.html')

    return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)


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
            return render_template('select_stock.html')
        return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)

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
            return render_template('select_stock.html')
        return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)

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


@app.route('/strategy/sma', methods=['GET'])
def strategy_sma():
    """SMA策略配置页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    strategy_type = session.get('strategy_type')
    run_mode = session.get('run_mode')

    # 检查是否有必要的信息
    if not stock_code or not stock_name:
        return render_template('select_stock.html')
    if not strategy_type:
        return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)
    if not run_mode:
        return render_template('select_mode.html',
                             stock_code=stock_code,
                             stock_name=stock_name,
                             strategy_type=strategy_type,
                             strategy_name=session.get('strategy_name', 'SMA'))

    return render_template('strategy_sma.html', stock_code=stock_code, stock_name=stock_name)


@app.route('/strategy/mean_cost', methods=['GET'])
def strategy_mean_cost():
    """均值成本策略配置页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    strategy_type = session.get('strategy_type')
    run_mode = session.get('run_mode')

    if not stock_code or not stock_name:
        return render_template('select_stock.html')
    if not strategy_type:
        return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)
    if not run_mode:
        return render_template('select_mode.html',
                             stock_code=stock_code,
                             stock_name=stock_name,
                             strategy_type=strategy_type,
                             strategy_name=session.get('strategy_name', '均值成本'))

    return render_template('strategy_mean_cost.html', stock_code=stock_code, stock_name=stock_name)


@app.route('/strategy/fixed_amount', methods=['GET'])
def strategy_fixed_amount():
    """定投策略配置页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    strategy_type = session.get('strategy_type')
    run_mode = session.get('run_mode')

    if not stock_code or not stock_name:
        return render_template('select_stock.html')
    if not strategy_type:
        return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)
    if not run_mode:
        return render_template('select_mode.html',
                             stock_code=stock_code,
                             stock_name=stock_name,
                             strategy_type=strategy_type,
                             strategy_name=session.get('strategy_name', '定投'))

    return render_template('strategy_fixed_amount.html', stock_code=stock_code, stock_name=stock_name)


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
    lot = int(request.form.get('lot') or 100)
    cash = float(request.form.get('cash') or 100000.0)

    # 在启动线程前提取所有需要的表单参数（避免request context问题）
    fixed_amount = float(request.form.get('fixed_amount') or 1000.0) if strategy == 'fixed_amount' else None
    period = int(request.form.get('period') or 20) if strategy == 'sma' else None

    # 创建回测任务
    progress_mgr = get_progress_manager()
    task_id = progress_mgr.create_task()

    # 创建进度回调函数
    def progress_callback(current, total):
        progress_mgr.update_progress(task_id, current, total)

    # 在后台线程执行回测
    def run_backtest():
        try:
            # 根据策略类型执行回测（各策略内部自行获取所需数据）
            if strategy == 'mean_cost':
                res = stocks.run_mean_cost(symbol=symbol, start_date=start, end_date=end,
                                          lot_size=lot, init_cash=cash, source=source,
                                          progress_callback=progress_callback)
            elif strategy == 'fixed_amount':
                res = stocks.run_fixed_amount(symbol=symbol, start_date=start, end_date=end,
                                            fixed_amount=fixed_amount, lot_size=lot,
                                            init_cash=cash, source=source,
                                            progress_callback=progress_callback)
            else:  # sma
                res = stocks.run_sma_backtest(symbol=symbol, source=source, start_date=start, end_date=end,
                                             lot_size=lot, init_cash=cash, period=period,
                                             progress_callback=progress_callback)

            # 设置任务结果
            progress_mgr.set_result(task_id, res)

        except Exception as e:
            # 设置任务错误
            progress_mgr.set_error(task_id, str(e))

    # 启动后台线程
    thread = threading.Thread(target=run_backtest, daemon=True)
    thread.start()

    # 返回进度页面
    return render_template('backtest_progress.html', task_id=task_id, symbol=symbol, strategy=strategy)


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


@app.route('/api/result/<task_id>')
def get_result(task_id):
    """获取回测结果"""
    progress_mgr = get_progress_manager()
    task = progress_mgr.get_task(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if task['status'] == 'error':
        return jsonify({'error': task['error']}), 500

    if task['status'] != 'completed':
        return jsonify({'error': '任务未完成'}), 400

    return jsonify({'result': task['result']})


@app.route('/view_result', methods=['POST'])
def view_result():
    """查看回测结果"""
    result_json = request.form.get('result_json')
    if not result_json:
        return render_template('result.html', error='无法获取回测结果')

    try:
        res = json.loads(result_json)
        # 使用详细模板显示结果
        if isinstance(res, dict) and ('trades_list' in res or 'history' in res):
            return render_template('result_mean.html', result=res)
        else:
            return render_template('result.html', error='回测结果格式不正确')
    except Exception as e:
        return render_template('result.html', error=f'解析结果失败: {e}')


if __name__ == '__main__':
    app.run(debug=True)
