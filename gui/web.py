import os
import sys
import json
from flask import Flask, render_template, request, session, jsonify

# Ensure project root is on sys.path so sibling packages (e.g. `source`) can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import stocks

app = Flask(__name__, template_folder='templates')
app.secret_key = 'stocks-quantitative-backtest-secret-key-2024'  # 用于session加密


def load_stock_list():
    """加载股票列表映射"""
    stock_file = os.path.join(os.path.dirname(__file__), 'stock_list.json')
    with open(stock_file, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    
    stock_list = load_stock_list()
    
    # 精确匹配股票代码
    for stock in stock_list:
        if stock['code'] == query:
            return jsonify({'code': stock['code'], 'name': stock['name']})
    
    # 精确匹配股票名称
    for stock in stock_list:
        if stock['name'] == query:
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


@app.route('/select_strategy', methods=['GET'])
def select_strategy():
    """策略选择页面"""
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    
    if not stock_code or not stock_name:
        # 如果没有选择股票，跳转回首页
        return render_template('select_stock.html')
    
    return render_template('select_strategy.html', stock_code=stock_code, stock_name=stock_name)


@app.route('/strategy/sma', methods=['GET'])
def strategy_sma():
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    
    if not stock_code or not stock_name:
        return render_template('select_stock.html')
    
    return render_template('strategy_sma.html', stock_code=stock_code, stock_name=stock_name)


@app.route('/strategy/mean_cost', methods=['GET'])
def strategy_mean_cost():
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    
    if not stock_code or not stock_name:
        return render_template('select_stock.html')
    
    return render_template('strategy_mean_cost.html', stock_code=stock_code, stock_name=stock_name)


@app.route('/strategy/fixed_amount', methods=['GET'])
def strategy_fixed_amount():
    stock_code = session.get('stock_code')
    stock_name = session.get('stock_name')
    
    if not stock_code or not stock_name:
        return render_template('select_stock.html')
    
    return render_template('strategy_fixed_amount.html', stock_code=stock_code, stock_name=stock_name)


@app.route('/run', methods=['POST'])
def run():
    # 从session获取股票信息
    symbol = session.get('stock_code')
    if not symbol:
        # 如果session中没有股票信息，回退到从表单获取（向后兼容）
        symbol = request.form.get('symbol', '600900').strip()
    
    source = request.form.get('source', 'auto')
    strategy = request.form.get('strategy', 'sma')
    lot = int(request.form.get('lot') or 100)
    cash = float(request.form.get('cash') or 100000.0)
    start = request.form.get('start') or None
    end = request.form.get('end') or None

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

        return render_template('result_mean.html', result=res)

    if strategy == 'fixed_amount':
        try:
            fixed_amount = float(request.form.get('fixed_amount') or 1000.0)
            res = stocks.run_fixed_amount(symbol=symbol, start_date=start, end_date=end, 
                                        fixed_amount=fixed_amount, lot_size=lot, 
                                        init_cash=cash, source=source)
        except Exception as e:
            return render_template('result.html', error=f"模拟运行失败: {e}")

        return render_template('result_mean.html', result=res)

    # 默认使用 stocks 提供的 SMA 回测封装，返回统一结构以便前端展示
    try:
        period = int(request.form.get('period') or 20)
        res = stocks.run_sma_backtest(symbol=symbol, source=source, start_date=start, end_date=end, 
                                     lot_size=lot, init_cash=cash, period=period)
    except Exception as e:
        return render_template('result.html', error=f"回测运行失败: {e}")

    # 如果返回了详细的交易流水（兼容 simulate_* 接口），使用详细模板；否则回退到摘要模板以兼容旧行为或测试桩
    if isinstance(res, dict) and ('trades_list' in res or 'history' in res):
        return render_template('result_mean.html', result=res)

    rows = len(df)
    start = res.get('start_date', '') if isinstance(res, dict) else ''
    end = res.get('end_date', '') if isinstance(res, dict) else ''
    init_value = res.get('init_cash') if isinstance(res, dict) else None
    final_value = res.get('final_cash') if isinstance(res, dict) else None

    return render_template('result.html', symbol=symbol, source=source, rows=rows, start=start, end=end, init=init_value, final=final_value)


if __name__ == '__main__':
    app.run(debug=True)
