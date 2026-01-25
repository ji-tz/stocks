#!/usr/bin/env python3
import argparse
import pprint

from solver.mean_cost_strategy import simulate_mean_cost


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--symbol', '-s', default='600900')
    p.add_argument('--start', default='20250101')
    p.add_argument('--source', default='auto')
    p.add_argument('--lot', type=int, default=100)
    p.add_argument('--cash', type=float, default=100000.0)
    args = p.parse_args()

    res = simulate_mean_cost(symbol=args.symbol, start_date=args.start, lot_size=args.lot, init_cash=args.cash, source=args.source)
    pprint.pprint(res)


if __name__ == '__main__':
    main()
