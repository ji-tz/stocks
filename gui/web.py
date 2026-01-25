import os
import sys
from flask import Flask, render_template, request

# Ensure project root is on sys.path so sibling packages (e.g. `source`) can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import stocks

app = Flask(__name__, template_folder='templates')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


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

        return render_template('result_mean.html', result=res)

    # 默认使用 stocks 提供的 SMA 回测封装
    try:
        res = stocks.run_sma_backtest(symbol=symbol, source=source, start_date=start, end_date=end)
    except Exception as e:
        return render_template('result.html', error=f"回测运行失败: {e}")

    rows = len(df)
    start = res.get('start_date', '')
    end = res.get('end_date', '')
    init_value = res.get('init_cash')
    final_value = res.get('final_cash')

    return render_template('result.html', symbol=symbol, source=source, rows=rows, start=start, end=end, init=init_value, final=final_value)


if __name__ == '__main__':
    app.run(debug=True)
