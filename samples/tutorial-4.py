from pytradelab import strategy
from pytradelab.barfeed import yahoofeed
from pytradelab.technical import ma

class MyStrategy(strategy.Strategy):
    def __init__(self, feed, smaPeriod):
        strategy.Strategy.__init__(self, feed, 1000)
        self.__sma = ma.SMA(feed["orcl"].get_close_data_series(), smaPeriod)
        self.__position = None

    def on_start(self):
        print "Initial portfolio value: $%.2f" % self.get_broker().get_cash()

    def on_enter_ok(self, position):
        execInfo = position.get_entry_order().get_execution_info()
        print "%s: BUY at $%.2f" % (execInfo.get_date_time(), execInfo.get_price())

    def on_enter_canceled(self, position):
        self.__position = None

    def on_exit_ok(self, position):
        execInfo = position.get_exit_order().get_execution_info()
        print "%s: SELL at $%.2f" % (execInfo.get_date_time(), execInfo.get_price())
        self.__position = None

    def on_exit_canceled(self, position):
        # If the exit was canceled, re-submit it.
        self.exit_position(self.__position)

    def on_bars(self, bars):
        # Wait for enough bars to be available to calculate a SMA.
        if self.__sma[-1] is None:
            return

        bar = bars["orcl"]
        # If a position was not opened, check if we should enter a long position.
        if self.__position == None:
            if bar.get_close() > self.__sma[-1]:
                # Enter a buy market order for 10 orcl shares. The order is good till canceled.
                self.__position = self.enter_long("orcl", 10, True)
        # Check if we have to exit the position.
        elif bar.get_close() < self.__sma[-1]:
             self.exit_position(self.__position)

    def on_finish(self, bars):
        print "Final portfolio value: $%.2f" % self.get_broker().get_equity()

def run_strategy(smaPeriod):
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.add_bars_from_csv("orcl", "orcl-2000.csv")

    # Evaluate the strategy with the feed's bars.
    myStrategy = MyStrategy(feed, smaPeriod)
    myStrategy.run()

run_strategy(15)

