from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma

class MyStrategy(strategy.Strategy):
    def __init__(self, feed):
        strategy.Strategy.__init__(self, feed)
        # We want a 15 period SMA over the closing prices.
        self.__sma = ma.SMA(feed["orcl"].get_close_data_series(), 15)

    def on_bars(self, bars):
        bar = bars["orcl"]
        print "%s: %s %s" % (bar.get_date_time(), bar.get_close(), self.__sma[-1])

# Load the yahoo feed from the CSV file
feed = yahoofeed.Feed()
feed.add_bars_from_csv("orcl", "orcl-2000.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = MyStrategy(feed)
myStrategy.run()

