from pytradelib import strategy
from pytradelib.barfeed import yahoofeed
from pytradelib.technical import ma
from pytradelib.technical import rsi

class MyStrategy(strategy.Strategy):
    def __init__(self, feed):
        strategy.Strategy.__init__(self, feed)
        self.__rsi = rsi.RSI(feed["orcl"].get_close_data_series(), 14)
        self.__sma = ma.SMA(self.__rsi, 15)

    def on_bars(self, bars):
        bar = bars["orcl"]
        print "%s: %s %s %s" % (bar.get_date_time(), bar.get_close(), self.__rsi[-1], self.__sma[-1])

# Load the yahoo feed from the CSV file
feed = yahoofeed.Feed()
feed.add_bars_from_csv("orcl", "orcl-2000.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = MyStrategy(feed)
myStrategy.run()

