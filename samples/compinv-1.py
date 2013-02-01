from pytradelab import strategy
from pytradelab.barfeed import yahoofeed
from pytradelab.stratanalyzer import returns
from pytradelab.stratanalyzer import sharpe
from pytradelab import broker
from pytradelab.utils import stats

class MyStrategy(strategy.Strategy):
    def __init__(self, feed):
        strategy.Strategy.__init__(self, feed, 1000000)

        # We wan't to use adjusted close prices instead of close.
        self.get_broker().set_use_adj_values(True)

        # Place the orders to get them processed on the first bar.
        orders = {
            "aeti": 297810,
            "egan": 81266,
            "glng": 11095,
            "simo": 17293,
        }
        for symbol, quantity in orders.items():
            o =  self.get_broker().create_market_order(broker.Order.Action.BUY, symbol, quantity, on_close=True)
            self.get_broker().place_order(o)

    def on_bars(self, bars):
        pass

# Load the yahoo feed from CSV files.
feed = yahoofeed.Feed()
feed.add_bars_from_csv("aeti", "aeti-2011-yahoofinance.csv")
feed.add_bars_from_csv("egan", "egan-2011-yahoofinance.csv")
feed.add_bars_from_csv("glng", "glng-2011-yahoofinance.csv")
feed.add_bars_from_csv("simo", "simo-2011-yahoofinance.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = MyStrategy(feed)

# Attach returns and sharpe ratio analyzers.
retAnalyzer = returns.Returns()
myStrategy.attach_analyzer(retAnalyzer)
sharpeRatioAnalyzer = sharpe.SharpeRatio()
myStrategy.attach_analyzer(sharpeRatioAnalyzer)

# Run the strategy
myStrategy.run()

# Print the results.
print "Final portfolio value: $%.2f" % myStrategy.get_result()
print "Anual return: %.2f %%" % (retAnalyzer.get_cumulative_returns()[-1] * 100)
print "Average daily return: %.2f %%" % (stats.mean(retAnalyzer.get_returns()) * 100)
print "Std. dev. daily return: %.4f" % (stats.stddev(retAnalyzer.get_returns()))
print "Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.get_sharpe_ratio(0, 252))

