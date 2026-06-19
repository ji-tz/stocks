#!/usr/bin/env python3
"""Add 'market' field to gui/stock_list.json based on code prefix."""

import json
import re

def get_market(code):
    if code.endswith('.HK'):
        return 'hk'
    match = re.match(r'^(\d)', code)
    if not match:
        return 'unknown'
    first_digit = match.group(1)
    if first_digit == '6':
        return 'sh'
    elif first_digit in ('0', '3'):
        return 'sz'
    elif first_digit == '8':
        return 'bj'
    else:
        return 'unknown'

def main():
    with open('gui/stock_list.json', 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    for stock in stocks:
        market = get_market(stock['code'])
        stock['market'] = market

    with open('gui/stock_list.json', 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f"Done. Updated {len(stocks)} stocks with market field.")

    # Verify
    markets = {}
    for s in stocks:
        m = s['market']
        markets[m] = markets.get(m, 0) + 1
    print(f"Market distribution: {json.dumps(markets, ensure_ascii=False)}")

if __name__ == '__main__':
    main()
