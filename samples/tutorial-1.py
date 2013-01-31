from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed

class MyStrategy(strategy.Strategy):
    def __init__(self, feed):
        strategy.Strategy.__init__(self, feed)

    def on_bars(self, bars):
        bar = bars["orcl"]
        print "%s: %s" % (bar.get_date_time(), bar.get_close())

# Load the yahoo feed from the CSV file
feed = yahoofeed.Feed()
feed.add_bars_from_csv("orcl", "orcl-2000.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = MyStrategy(feed)
myStrategy.run()

