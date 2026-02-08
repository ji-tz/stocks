import os
import sys
import json
from flask import Flask, render_template, request, session, jsonify
from flask import Flask, render_template, request, jsonify

# Ensure project root is on sys.path so sibling packages (e.g. `source`) can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import stocks
import backtest_records

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

    try:
        # 使用后端提供的统一接口获取数据（可传入日期范围）
        if start or end:
            df = stocks.get_data(symbol=symbol, source=source, start_date=start or None, end_date=end or None)
        else:
            df = stocks.get_data(symbol=symbol, source=source)
    except Exception as e:
        return render_template('result.html', error=str(e))

    if strategy == 'mean_cost':
        try:
            res = stocks.run_mean_cost(symbol=symbol, start_date=start, end_date=end, lot_size=lot, init_cash=cash, source=source)
        except Exception as e:
            return render_template('result.html', error=f"模拟运行失败: {e}")

        # 保存回测记录
        backtest_records.add_record(
            strategy='mean_cost',
            symbol=symbol,
            parameters={'start': start, 'end': end, 'lot': lot, 'cash': cash, 'source': source},
            result=res
        )

        return render_template('result_mean.html', result=res)

    if strategy == 'fixed_amount':
        try:
            fixed_amount = float(request.form.get('fixed_amount') or 1000.0)
            res = stocks.run_fixed_amount(symbol=symbol, start_date=start, end_date=end, 
                                        fixed_amount=fixed_amount, lot_size=lot, 
                                        init_cash=cash, source=source)
        except Exception as e:
            return render_template('result.html', error=f"模拟运行失败: {e}")

        # 保存回测记录
        backtest_records.add_record(
            strategy='fixed_amount',
            symbol=symbol,
            parameters={'start': start, 'end': end, 'fixed_amount': fixed_amount, 'lot': lot, 'cash': cash, 'source': source},
            result=res
        )

        return render_template('result_mean.html', result=res)

    # 默认使用 stocks 提供的 SMA 回测封装，返回统一结构以便前端展示
    try:
        period = int(request.form.get('period') or 20)
        res = stocks.run_sma_backtest(symbol=symbol, source=source, start_date=start, end_date=end, 
                                     lot_size=lot, init_cash=cash, period=period)
    except Exception as e:
        return render_template('result.html', error=f"回测运行失败: {e}")

    # 保存回测记录
    backtest_records.add_record(
        strategy='sma',
        symbol=symbol,
        parameters={'start': start, 'end': end, 'period': period, 'lot': lot, 'cash': cash, 'source': source},
        result=res
    )

    # 如果返回了详细的交易流水（兼容 simulate_* 接口），使用详细模板；否则回退到摘要模板以兼容旧行为或测试桩
    if isinstance(res, dict) and ('trades_list' in res or 'history' in res):
        return render_template('result_mean.html', result=res)

    rows = len(df)
    start = res.get('start_date', '') if isinstance(res, dict) else ''
    end = res.get('end_date', '') if isinstance(res, dict) else ''
    init_value = res.get('init_cash') if isinstance(res, dict) else None
    final_value = res.get('final_cash') if isinstance(res, dict) else None

    return render_template('result.html', symbol=symbol, source=source, rows=rows, start=start, end=end, init=init_value, final=final_value)


@app.route('/history', methods=['GET'])
def history():
    """历史记录列表页面"""
    records = backtest_records.get_records()
    return render_template('history.html', records=records)


@app.route('/compare', methods=['GET'])
def compare():
    """对比页面"""
    # 从查询参数获取要对比的记录ID列表
    record_ids = request.args.getlist('ids')
    
    # 获取记录详情
    records = []
    for record_id in record_ids:
        record = backtest_records.get_record(record_id)
        if record:
            records.append(record)
    
    return render_template('compare.html', records=records)


@app.route('/api/records', methods=['GET'])
def api_records():
    """获取记录列表的JSON API"""
    records = backtest_records.get_records()
    return jsonify({'records': records})


@app.route('/api/record/<record_id>', methods=['GET'])
def api_record(record_id):
    """获取单条记录的JSON API"""
    record = backtest_records.get_record(record_id)
    if record:
        return jsonify(record)
    return jsonify({'error': 'Record not found'}), 404


@app.route('/api/record/<record_id>', methods=['DELETE'])
def api_delete_record(record_id):
    """删除记录的JSON API"""
    success = backtest_records.delete_record(record_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Record not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)
