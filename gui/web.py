import os
import sys
from flask import Flask, render_template, request, jsonify

# Ensure project root is on sys.path so sibling packages (e.g. `source`) can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import stocks
import backtest_records

app = Flask(__name__, template_folder='templates')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/strategy/sma', methods=['GET'])
def strategy_sma():
    return render_template('strategy_sma.html')


@app.route('/strategy/mean_cost', methods=['GET'])
def strategy_mean_cost():
    return render_template('strategy_mean_cost.html')


@app.route('/strategy/fixed_amount', methods=['GET'])
def strategy_fixed_amount():
    return render_template('strategy_fixed_amount.html')


@app.route('/run', methods=['POST'])
def run():
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
