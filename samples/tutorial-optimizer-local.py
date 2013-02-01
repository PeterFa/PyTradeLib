import itertools
from pytradelab.optimizer import local
from pytradelab.barfeed import yahoofeed
from pytradelab import strategy
from pytradelab.technical import ma
from pytradelab.technical import rsi

class MyStrategy(strategy.Strategy):
    def __init__(self, feed, entrySMA, exitSMA, rsiPeriod, overBoughtThreshold, overSoldThreshold):
        strategy.Strategy.__init__(self, feed, 2000)
        ds = feed["dia"].get_close_data_series()
        self.__entrySMA = ma.SMA(ds, entrySMA)
        self.__exitSMA = ma.SMA(ds, exitSMA)
        self.__rsi = rsi.RSI(ds, rsiPeriod)
        self.__overBoughtThreshold = overBoughtThreshold
        self.__overSoldThreshold = overSoldThreshold
        self.__longPos = None
        self.__shortPos = None

    def on_enter_ok(self, position):
        pass

    def on_enter_canceled(self, position):
        if self.__longPos == position:
            self.__longPos = None
        elif self.__shortPos == position:
            self.__shortPos = None
        else:
            assert(False)

    def on_exit_ok(self, position):
        if self.__longPos == position:
            self.__longPos = None
        elif self.__shortPos == position:
            self.__shortPos = None
        else:
            assert(False)

    def on_exit_canceled(self, position):
        # If the exit was canceled, re-submit it.
        self.exit_position(position)

    def on_bars(self, bars):
        # Wait for enough bars to be available to calculate SMA and RSI.
        if self.__exitSMA[-1] is None or self.__entrySMA[-1] is None or self.__rsi[-1] is None:
            return

        bar = bars["dia"]
        if self.__longPos != None:
            if self.exitLongSignal(bar):
                self.exit_position(self.__longPos)
        elif self.__shortPos != None:
            if self.exitShortSignal(bar):
                self.exit_position(self.__shortPos)
        else:
            if self.enter_longSignal(bar):
                self.__longPos = self.enter_long("dia", 10, True)
            elif self.enter_shortSignal(bar):
                self.__shortPos = self.enter_short("dia", 10, True)

    def enter_longSignal(self, bar):
        return bar.get_close() > self.__entrySMA[-1] and self.__rsi[-1] <= self.__overSoldThreshold

    def exitLongSignal(self, bar):
        return bar.get_close() > self.__exitSMA[-1]

    def enter_shortSignal(self, bar):
        return bar.get_close() < self.__entrySMA[-1] and self.__rsi[-1] >= self.__overBoughtThreshold

    def exitShortSignal(self, bar):
        return bar.get_close() < self.__exitSMA[-1]

def parameters_generator():
    entrySMA = range(150, 251)
    exitSMA = range(5, 16)
    rsiPeriod = range(2, 11)
    overBoughtThreshold = range(75, 96)
    overSoldThreshold = range(5, 26)
    return itertools.product(entrySMA, exitSMA, rsiPeriod, overBoughtThreshold, overSoldThreshold)

# The if __name__ == '__main__' part is necessary if running on Windows.
if __name__ == '__main__':
    # Load the feed from the CSV files.
    feed = yahoofeed.Feed()
    feed.add_bars_from_csv("dia", "dia-2009.csv")
    feed.add_bars_from_csv("dia", "dia-2010.csv")
    feed.add_bars_from_csv("dia", "dia-2011.csv")

    local.run(MyStrategy, feed, parameters_generator())

