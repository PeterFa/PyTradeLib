import csv
import datetime
import os

from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade import strategy
from pyalgotrade import broker
from pyalgotrade.utils import stats
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.stratanalyzer import sharpe

class OrdersFile:
    def __init__(self, ordersFile):
        self.__orders = {}
        self.__firstDate = None
        self.__lastDate = None
        self.__symbols = []

        # Load orders from the file.
        reader = csv.DictReader(open(ordersFile, "r"), fieldnames=["year", "month", "day", "symbol", "action", "qty"])
        for row in reader:
            date_time = datetime.datetime(int(row["year"]), int(row["month"]), int(row["day"]))
            self.__orders.setdefault(date_time, [])
            order = (row["symbol"], row["action"], int(row["qty"]))
            self.__orders[date_time].append(order)

            # As we process the file, store symbols, first date, and last date.
            if row["symbol"] not in self.__symbols:
                self.__symbols.append(row["symbol"])

            if self.__firstDate == None:
                self.__firstDate = date_time
            else:
                self.__firstDate = min(self.__firstDate, date_time)

            if self.__lastDate == None:
                self.__lastDate = date_time
            else:
                self.__lastDate = max(self.__lastDate, date_time)

    def getFirstDate(self):
        return self.__firstDate

    def getLastDate(self):
        return self.__lastDate

    def get_symbols(self):
        return self.__symbols

    def getOrders(self, date_time):
        return self.__orders.get(date_time, [])

class MyStrategy(strategy.Strategy):
    def __init__(self, feed, cash, ordersFile, use_adjustedClose):
        # Suscribe to the feed bars event before the broker just to place the orders properly.
        feed.get_new_bars_event().subscribe(self.__on_barsBeforeBroker)
        strategy.Strategy.__init__(self, feed, cash)
        self.__ordersFile = ordersFile
        self.get_broker().set_use_adj_values(use_adjustedClose)
        # We will allow buying more shares than cash allows.
        self.get_broker().set_allow_negative_cash(True)

    def __on_barsBeforeBroker(self, bars):
        for symbol, action, quantity in self.__ordersFile.getOrders(bars.get_date_time()):
            if action.lower() == "buy":
                action = broker.Order.Action.BUY
            else:
                action = broker.Order.Action.SELL
            o = self.get_broker().create_market_order(action, symbol, quantity, on_close=True)
            self.get_broker().place_order(o)

    def on_order_updated(self, order):
        execInfo = order.get_execution_info()
        if not execInfo:
            raise Exception("Order canceled. Ran out of cash ?")

    def on_bars(self, bars):
        portfolioValue = self.get_broker().get_equity()
        print "%s: Portfolio value: $%.2f" % (bars.get_date_time(), portfolioValue)

def main():
    # Load the orders file.
    ordersFile = OrdersFile("orders.csv")
    print "First date", ordersFile.getFirstDate()
    print "Last date", ordersFile.getLastDate()
    print "Symbols", ordersFile.get_symbols()

    # Load the data from QSTK storage. QS environment variable has to be defined.
    feed = yahoofeed.Feed()
    feed.set_bar_filter(csvfeed.DateRangeFilter(ordersFile.getFirstDate(), ordersFile.getLastDate()))
    feed.set_daily_bar_time(datetime.time(0, 0, 0)) # This is to match the dates loaded with the ones in the orders file.
    for symbol in ordersFile.get_symbols():
        feed.add_bars_from_csv(symbol, os.path.join(os.getenv("QS"), "QSData", "Yahoo", symbol + ".csv"))

    # Run the strategy.
    cash = 1000000
    use_adjustedClose = True
    myStrategy = MyStrategy(feed, cash, ordersFile, use_adjustedClose)

    # Attach returns and sharpe ratio analyzers.
    retAnalyzer = returns.Returns()
    myStrategy.attach_analyzer(retAnalyzer)
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    myStrategy.attach_analyzer(sharpeRatioAnalyzer)

    myStrategy.run()

    # Print the results.
    print "Final portfolio value: $%.2f" % myStrategy.get_result()
    print "Anual return: %.2f %%" % (retAnalyzer.get_cumulative_returns()[-1] * 100)
    print "Average daily return: %.2f %%" % (stats.mean(retAnalyzer.get_returns()) * 100)
    print "Std. dev. daily return: %.4f" % (stats.stddev(retAnalyzer.get_returns()))
    print "Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.get_sharpe_ratio(0, 252))

main()

