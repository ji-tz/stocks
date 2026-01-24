import backtrader as bt

class SmaStrategy(bt.Strategy):
    params = (('period', 20),)
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.period)
    def next(self):
        if not self.position:
            if self.datas[0].close[0] > self.sma[0]:
                self.buy()
        else:
            if self.datas[0].close[0] < self.sma[0]:
                self.sell()
