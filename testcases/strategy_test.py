# This file was originally part of PyAlgoTrade.
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import unittest
import datetime
import threading
import Queue
import time
import pytz

from pytradelab import strategy
from pytradelab import barfeed
from pytradelab import broker
from pytradelab.broker import backtesting
from pytradelab.barfeed import csvfeed
from pytradelab.barfeed import yahoofeed
from pytradelab.barfeed import ninjatraderfeed
from pytradelab.utils import dt
from pytradelab import marketsession
import common

def us_equities_datetime(*params):
    ret = datetime.datetime(*params)
    ret = dt.localize(ret, marketsession.USEquities.getTimezone())
    return ret

def datetime_from_date(year, month, day):
    ret = datetime.datetime(year, month, day)
    ret = datetime.datetime.combine(ret, datetime.time(23, 59, 59))
    return ret

# This class decorates a barfeed.BarFeed and simulates an external barfeed that lives in a different thread.
class ExternalBarFeed(barfeed.BasicBarFeed):
    def __init__(self, decoratedBarFeed):
        barfeed.BasicBarFeed.__init__(self, decoratedBarFeed.get_frequency())
        self.__decorated = decoratedBarFeed
        self.__stopped = False
        self.__stop_dispatching = False

        # The barfeed runs in its own thread and will put bars in a queue that will be consumed by the strategy when fetch_next_bars is called.
        self.__queue = Queue.Queue()

        # We're wrapping the barfeed so we need to register the same symbols.
        for symbol in decoratedBarFeed.get_registered_symbols():
            self.register_symbol(symbol)

        # This is the thread that will run the barfeed.
        self.__thread = threading.Thread(target=self.__threadMain)

    def __threadMain(self):
        self.__decorated.start()

        # Just consume the bars and put them in a queue.
        bars = self.__decorated.get_next_bars()
        while bars != None and not self.__stopped:
            self.__queue.put(bars)
            bars = self.__decorated.get_next_bars()

        # Flag end of barfeed
        self.__queue.put(None)
        self.__decorated.stop()
        self.__decorated.join()

    def get_next_bars(self):
        # Consume the bars from the queue.
        ret = None
        try:
            # If there is nothing there after 5 seconds, then treat this as the end.
            ret = self.__queue.get(True, 5)
        except Queue.Empty:
            self.__stop_dispatching = True
            ret = None
        return ret

    def start(self):
        self.__thread.start()

    def stop(self):
        self.__stopped = True

    def join(self):
        self.__thread.join()

    def stop_dispatching(self):
        return self.__stop_dispatching

class ExternalBroker(broker.Broker):
    def __init__(self, cash, bar_feed, commission=None):
        broker.Broker.__init__(self)

        self.__ordersQueue = Queue.Queue()
        self.__stop = False

        # We're using a backtesting broker which only processes orders when bars are recevied.
        self.__decorated = backtesting.Broker(cash, bar_feed, commission)
        # We'll queue events from the backtesting broker and forward those ONLY when dispatch is called.
        self.__decorated.get_order_updated_event().subscribe(self.__on_order_updated)

        self.__thread = threading.Thread(target=self.__threadMain)

    def __on_order_updated(self, broker_, order):
        self.__ordersQueue.put(order)

    def __threadMain(self):
        self.__decorated.start()

        # There is nothing special to do here since the backtesting broker will run when barfeed events are processed.
        while not self.__stop or not self.__ordersQueue.empty():
            time.sleep(1)

        self.__decorated.stop()
        self.__decorated.join()

    def set_cash(self, cash):
        self.__decorated.set_cash(cash)

    def get_cash(self):
        return self.__decorated.get_cash()

    def set_use_adj_values(self, use_adjusted):
        self.__decorated.set_use_adj_values(use_adjusted)

    def start(self):
        self.__thread.start()

    def stop(self):
        self.__stop = True

    def join(self):
        self.__thread.join()

    # Return True if there are not more events to dispatch.
    def stop_dispatching(self):
        ret = self.__decorated.stop_dispatching() and self.__ordersQueue.empty()
        return ret

    # Dispatch events.
    def dispatch(self):
        # Get orders from the queue and emit events.
        try:
            while True:
                order = self.__ordersQueue.get(False)
                self.get_order_updated_event().emit(self, order)
        except Queue.Empty:
            pass
    
    def place_order(self, order):
        return self.__decorated.place_order(order)
    
    def create_market_order(self, action, symbol, quantity, on_close = False):
        return self.__decorated.create_market_order(action, symbol, quantity, on_close)

    def create_limit_order(self, action, symbol, limit_price, quantity):
        return self.__decorated.create_limit_order(action, symbol, limit_price, quantity)

    def create_stop_order(self, action, symbol, stop_price, quantity):
        return self.__decorated.create_stop_order(action, symbol, stop_price, quantity)

    def create_stop_limit_order(self, action, symbol, stop_price, limit_price, quantity):
        return self.__decorated.create_stop_limit_order(action, symbol, stop_price, limit_price, quantity)

    def cancel_order(self, order):
        return self.__decorated.cancel_order(order)

class TestStrategy(strategy.Strategy):
    def __init__(self, bar_feed, cash, broker_ = None):
        strategy.Strategy.__init__(self, bar_feed, cash, broker_)

        self.__activePosition = None
        # Maps dates to a tuple of (method, params)
        self.__posEntry = {}
        self.__posExit = {}
        # Maps dates to a tuple of (method, params)
        self.__orderEntry = {}

        self.__result = 0
        self.__net_profit = 0
        self.__orderUpdatedEvents = 0
        self.__enterOkEvents = 0
        self.__enterCanceledEvents = 0
        self.__exitOkEvents = 0
        self.__exitCanceledEvents = 0
        self.__exit_on_session_close = False
        self.__brokerOrdersGTC = False

    def addOrder(self, date_time, method, *methodParams):
        self.__orderEntry.setdefault(date_time, [])
        self.__orderEntry[date_time].append((method, methodParams))

    def addPosEntry(self, date_time, enterMethod, *methodParams):
        self.__posEntry.setdefault(date_time, [])
        self.__posEntry[date_time].append((enterMethod, methodParams))

    def addPosExit(self, date_time, exitMethod, *methodParams):
        self.__posExit.setdefault(date_time, [])
        self.__posExit[date_time].append((exitMethod, methodParams))

    def set_exit_on_session_close(self, exit_on_session_close):
        self.__exit_on_session_close = exit_on_session_close

    def setBrokerOrdersGTC(self, gtc):
        self.__brokerOrdersGTC = gtc

    def get_order_updated_events(self):
        return self.__orderUpdatedEvents

    def getEnterOkEvents(self):
        return self.__enterOkEvents

    def getExitOkEvents(self):
        return self.__exitOkEvents

    def getEnterCanceledEvents(self):
        return self.__enterCanceledEvents

    def getExitCanceledEvents(self):
        return self.__exitCanceledEvents

    def get_result(self):
        return self.__result

    def get_net_profit(self):
        return self.__net_profit

    def on_start(self):
        pass

    def on_order_updated(self, order):
        self.__orderUpdatedEvents += 1

    def on_enter_ok(self, position):
        # print "Enter ok", position.get_entry_order().get_execution_info().get_date_time()
        self.__enterOkEvents += 1
        if self.__activePosition == None:
            self.__activePosition = position
            self.__activePosition.set_exit_on_session_close(self.__exit_on_session_close)

    def on_enter_canceled(self, position):
        # print "Enter canceled", position.get_entry_order().get_execution_info().get_date_time()
        self.__enterCanceledEvents += 1
        self.__activePosition = None

    def on_exit_ok(self, position):
        # print "Exit ok", position.get_exit_order().get_execution_info().get_date_time()
        self.__result += position.get_result()
        self.__net_profit += position.get_net_profit()
        self.__exitOkEvents += 1
        self.__activePosition = None

    def on_exit_canceled(self, position):
        # print "Exit canceled", position.get_exit_order().get_execution_info().get_date_time()
        self.__exitCanceledEvents += 1

    def on_bars(self, bars):
        date_time = bars.get_date_time()

        # Check position entry.
        for meth, params in self.__posEntry.get(date_time, []):
            if self.__activePosition != None:
                raise Exception("Only one position allowed at a time")
            self.__activePosition = meth(*params)
            self.__activePosition.set_exit_on_session_close(self.__exit_on_session_close)

        # Check position exit.
        for meth, params in self.__posExit.get(date_time, []):
            if self.__activePosition == None:
                raise Exception("A position was not entered")
            meth(self.__activePosition, *params)

        # Check order entry.
        for meth, params in self.__orderEntry.get(date_time, []):
            order = meth(*params)
            order.set_good_until_canceled(self.__brokerOrdersGTC)
            self.get_broker().place_order(order)

class StrategyTestCase(unittest.TestCase):
    TestInstrument = "doesntmatter"

    def loadIntradayBarFeed(self):
        from_month=1
        to_month=1
        from_day=3
        to_day=3
        bar_filter = csvfeed.USEquitiesRTH(us_equities_datetime(2011, from_month, from_day, 00, 00), us_equities_datetime(2011, to_month, to_day, 23, 59))
        bar_feed = ninjatraderfeed.Feed(barfeed.Frequency.MINUTE)
        bar_feed.set_bar_filter(bar_filter)
        bar_feed.add_bars_from_csv(StrategyTestCase.TestInstrument, common.get_data_file_path("nt-spy-minute-2011.csv"))
        return bar_feed

    def loadDailyBarFeed(self):
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv(StrategyTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"))
        return bar_feed

    def createStrategy(self, simulateExternalBarFeed, simulateExternalBroker, useDailyBarFeed = True):
        if useDailyBarFeed:
            bar_feed = self.loadDailyBarFeed()
        else:
            bar_feed = self.loadIntradayBarFeed()

        if simulateExternalBarFeed:
            bar_feed = ExternalBarFeed(bar_feed)

        broker_ = None
        if simulateExternalBroker:
            broker_ = ExternalBroker(1000, bar_feed)

        strat = TestStrategy(bar_feed, 1000, broker_)
        return strat

class BrokerOrdersTestCase(StrategyTestCase):
    def testLimitOrder(self):
        strat = self.createStrategy(False, False)

        o = strat.get_broker().create_market_order(broker.Order.Action.BUY, StrategyTestCase.TestInstrument, 1)
        strat.get_broker().place_order(o)
        strat.run()
        self.assertTrue(o.is_filled())
        self.assertTrue(strat.get_order_updated_events() == 1)
    
class LongPosTestCase(StrategyTestCase):
    def __testLongPositionImpl(self, simulateExternalBarFeed, simulateExternalBroker):
        strat = self.createStrategy(simulateExternalBarFeed, simulateExternalBroker)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-08,27.37,27.50,24.50,24.81,63040000,24.26 - Sell
        # 2000-11-07,28.37,28.44,26.50,26.56,58950800,25.97 - Exit long
        # 2000-11-06,30.69,30.69,27.50,27.94,75552300,27.32 - Buy
        # 2000-11-03,31.50,31.75,29.50,30.31,65020900,29.64 - Enter long

        strat.addPosEntry(datetime_from_date(2000, 11, 3), strat.enter_long, StrategyTestCase.TestInstrument, 1, False)
        strat.addPosExit(datetime_from_date(2000, 11, 7), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.get_order_updated_events() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + 27.37 - 30.69, 2))
        self.assertTrue(round(strat.get_result(), 3) == -0.108)
        self.assertTrue(round(strat.get_net_profit(), 2) == round(27.37 - 30.69, 2))

    def testLongPosition(self):
        self.__testLongPositionImpl(False, False)

    def testLongPosition_ExternalBF(self):
        self.__testLongPositionImpl(True, False)

    def testLongPosition_ExternalBFAndBroker(self):
        self.__testLongPositionImpl(True, True)

    def __testLongPositionAdjCloseImpl(self, simulateExternalBarFeed, simulateExternalBroker):
        strat = self.createStrategy(simulateExternalBarFeed, simulateExternalBroker)
        strat.get_broker().set_use_adj_values(True)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-10-13,31.00,35.75,31.00,35.63,38516200,34.84
        # 2000-10-12,63.81,64.87,61.75,63.00,50892400,30.80
        # 2000-01-19,56.13,58.25,54.00,57.13,49208800,27.93
        # 2000-01-18,107.87,114.50,105.62,111.25,66791200,27.19

        strat.addPosEntry(datetime_from_date(2000, 1, 18), strat.enter_long, StrategyTestCase.TestInstrument, 1, False)
        strat.addPosExit(datetime_from_date(2000, 10, 12), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + 30.31 - 27.44, 2))
        self.assertTrue(round(strat.get_result(), 3) == 0.105)
        self.assertTrue(round(strat.get_net_profit(), 2) == round(30.31 - 27.44, 2))

    def testLongPositionAdjClose(self):
        self.__testLongPositionAdjCloseImpl(False, False)

    def testLongPositionAdjClose_ExternalBF(self):
        self.__testLongPositionAdjCloseImpl(True, False)

    def testLongPositionAdjClose_ExternalBFAndBroker(self):
        self.__testLongPositionAdjCloseImpl(True, True)

    def testLongPositionGTC(self):
        strat = self.createStrategy(False, False)
        strat.get_broker().set_cash(48)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-02-07,59.31,60.00,58.42,59.94,44697200,29.30
        # 2000-02-04,57.63,58.25,56.81,57.81,40925000,28.26 - sell succeeds
        # 2000-02-03,55.38,57.00,54.25,56.69,55540600,27.71 - exit
        # 2000-02-02,54.94,56.00,54.00,54.31,63940400,26.55
        # 2000-02-01,51.25,54.31,50.00,54.00,57108800,26.40
        # 2000-01-31,47.94,50.13,47.06,49.95,68152400,24.42 - buy succeeds
        # 2000-01-28,51.50,51.94,46.63,47.38,86400600,23.16 - buy fails
        # 2000-01-27,55.81,56.69,50.00,51.81,61061800,25.33 - enter_long

        strat.addPosEntry(datetime_from_date(2000, 1, 27), strat.enter_long, StrategyTestCase.TestInstrument, 1, True)
        strat.addPosExit(datetime_from_date(2000, 2, 3), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(48 + 57.63 - 47.94, 2))
        self.assertTrue(round(strat.get_net_profit(), 2) == round(57.63 - 47.94, 2))

    def testEntryCanceled(self):
        strat = self.createStrategy(False, False)
        strat.get_broker().set_cash(10)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-01-28,51.50,51.94,46.63,47.38,86400600,23.16 - buy fails
        # 2000-01-27,55.81,56.69,50.00,51.81,61061800,25.33 - enter_long

        strat.addPosEntry(datetime_from_date(2000, 1, 27), strat.enter_long, StrategyTestCase.TestInstrument, 1, False)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 0)
        self.assertTrue(strat.getEnterCanceledEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(strat.get_broker().get_cash() == 10)
        self.assertTrue(strat.get_net_profit() == 0)

    def testIntradayExitOnClose_EntryNotFilled(self):
        # Test that if the entry gets canceled, then the exit on close order doesn't get submitted.
        bar_feed = self.loadIntradayBarFeed()
        strat = TestStrategy(bar_feed, 1)
        strat.set_exit_on_session_close(True)

        strat.addPosEntry(us_equities_datetime(2011, 1, 3, 14, 30), strat.enter_long, StrategyTestCase.TestInstrument, 1, False)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 0)
        self.assertTrue(strat.getEnterCanceledEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)

    def testIntradayExitOnClose_AllInOneDay(self):
        bar_feed = self.loadIntradayBarFeed()
        strat = TestStrategy(bar_feed, 1000)
        strat.set_exit_on_session_close(True)

        # Enter on first bar, exit on close.
        strat.addPosEntry(us_equities_datetime(2011, 1, 3, 9, 30), strat.enter_long, StrategyTestCase.TestInstrument, 1, False)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + 127.05 - 126.71, 2))

    def testIntradayExitOnClose_BuyOnLastBar(self):
        bar_feed = self.loadIntradayBarFeed()
        strat = TestStrategy(bar_feed, 1000)
        strat.set_exit_on_session_close(True)

        # 3/Jan/2011 20:59:00 - Enter long
        # 3/Jan/2011 21:00:00 - Entry gets canceled.

        strat.addPosEntry(dt.localize(datetime.datetime(2011, 1, 3, 20, 59), pytz.utc), strat.enter_long, StrategyTestCase.TestInstrument, 1, True)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 0)
        self.assertTrue(strat.getEnterCanceledEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == 1000)

    def testIntradayExitOnClose_BuyOnPenultimateBar(self):
        bar_feed = self.loadIntradayBarFeed()
        strat = TestStrategy(bar_feed, 1000)
        strat.set_exit_on_session_close(True)

        # 3/Jan/2011 20:58:00 - Enter long
        # 3/Jan/2011 20:59:00 - entry gets filled
        # 3/Jan/2011 21:00:00 - exit gets filled.

        strat.addPosEntry(dt.localize(datetime.datetime(2011, 1, 3, 20, 58), pytz.utc), strat.enter_long, StrategyTestCase.TestInstrument, 1, True)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + 127.05 - 127.07, 2))

class ShortPosTestCase(StrategyTestCase):
    def __testShortPositionImpl(self, simulateExternalBarFeed, simulateExternalBroker):
        strat = self.createStrategy(simulateExternalBarFeed, simulateExternalBroker)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-08,27.37,27.50,24.50,24.81,63040000,24.26
        # 2000-11-07,28.37,28.44,26.50,26.56,58950800,25.97
        # 2000-11-06,30.69,30.69,27.50,27.94,75552300,27.32
        # 2000-11-03,31.50,31.75,29.50,30.31,65020900,29.64

        strat.addPosEntry(datetime_from_date(2000, 11, 3), strat.enter_short, StrategyTestCase.TestInstrument, 1, False)
        strat.addPosExit(datetime_from_date(2000, 11, 7), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + 30.69 - 27.37, 2))
        self.assertTrue(round(strat.get_result(), 3) == round(0.10817856, 3))
        self.assertTrue(round(strat.get_net_profit(), 2) == round(30.69 - 27.37, 2))

    def testShortPosition(self):
        self.__testShortPositionImpl(False, False)

    def testShortPosition_ExternalBF(self):
        self.__testShortPositionImpl(True, False)

    def testShortPosition_ExternalBFAndBroker(self):
        self.__testShortPositionImpl(True, True)
    
    def __testShortPositionAdjCloseImpl(self, simulateExternalBarFeed, simulateExternalBroker):
        strat = self.createStrategy(simulateExternalBarFeed, simulateExternalBroker)
        strat.get_broker().set_use_adj_values(True)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-10-13,31.00,35.75,31.00,35.63,38516200,34.84
        # 2000-10-12,63.81,64.87,61.75,63.00,50892400,30.80
        # 2000-01-19,56.13,58.25,54.00,57.13,49208800,27.93
        # 2000-01-18,107.87,114.50,105.62,111.25,66791200,27.19

        strat.addPosEntry(datetime_from_date(2000, 1, 18), strat.enter_short, StrategyTestCase.TestInstrument, 1, False)
        strat.addPosExit(datetime_from_date(2000, 10, 12), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + 27.44 - 30.31, 2))
        self.assertTrue(round(strat.get_result(), 3) == round(-0.104591837, 3))
        self.assertTrue(round(strat.get_net_profit(), 2) == round(27.44 - 30.31, 2))

    def testShortPositionAdjClose(self):
        self.__testShortPositionAdjCloseImpl(False, False)

    def testShortPositionAdjClose_ExternalBF(self):
        self.__testShortPositionAdjCloseImpl(True, False)

    def testShortPositionAdjClose_ExternalBFAndBroker(self):
        self.__testShortPositionAdjCloseImpl(True, True)

    def __testShortPosition_exit_canceledImpl(self, simulateExternalBarFeed, simulateExternalBroker):
        strat = self.createStrategy(simulateExternalBarFeed, simulateExternalBroker)
        strat.get_broker().set_cash(0)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-12-08,30.06,30.62,29.25,30.06,40054100,29.39
        # 2000-12-07,29.62,29.94,28.12,28.31,41093000,27.68
        # .
        # 2000-11-29,23.19,23.62,21.81,22.87,75408100,22.36
        # 2000-11-28,23.50,23.81,22.25,22.66,43078300,22.16

        strat.addPosEntry(datetime_from_date(2000, 11, 28), strat.enter_short, StrategyTestCase.TestInstrument, 1, False)
        strat.addPosExit(datetime_from_date(2000, 12, 7), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == 23.19)
        self.assertTrue(strat.get_net_profit() == 0)

    def testShortPosition_exit_canceled(self):
        self.__testShortPosition_exit_canceledImpl(False, False)

    def testShortPosition_exit_canceled_ExternalBF(self):
        self.__testShortPosition_exit_canceledImpl(True, False)

    def testShortPosition_exit_canceled_ExternalBFAndBroker(self):
        self.__testShortPosition_exit_canceledImpl(True, True)

    def testShortPosition_exit_canceledAndReSubmitted(self):
        strat = self.createStrategy(False, False)
        strat.get_broker().set_cash(0)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-24,23.31,24.25,23.12,24.12,22446100,23.58
        # 2000-11-22,23.62,24.06,22.06,22.31,53317000,21.81 - exitShort that gets filled
        # 2000-11-21,24.81,25.62,23.50,23.87,58651900,23.34
        # 2000-11-20,24.31,25.87,24.00,24.75,89783100,24.20
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74 - exitShort that gets canceled
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_short

        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_short, StrategyTestCase.TestInstrument, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 14), strat.exit_position)
        strat.addPosExit(datetime_from_date(2000, 11, 22), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(25.12 - 23.31, 2))

    def testIntradayExitOnClose(self):
        bar_feed = self.loadIntradayBarFeed()
        strat = TestStrategy(bar_feed, 1000)
        strat.set_exit_on_session_close(True)

        # 3/Jan/2011 18:20:00 - Short sell
        # 3/Jan/2011 18:21:00 - Sell at open price: 127.4
        # .
        # 3/Jan/2011 21:00:00 - Exit on close - Buy at close price: 127.05
        # The exit date should not be triggered

        strat.addPosEntry(us_equities_datetime(2011, 1, 3, 13, 20), strat.enter_short, StrategyTestCase.TestInstrument, 1, True)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.4 - 127.05), 2))
        self.assertTrue(round(strat.get_net_profit(), 2) == round(127.4 - 127.05, 2))

class LimitPosTestCase(StrategyTestCase):
    def testLong(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - exit filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - exit_position
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - entry filled
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_limit
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_limit, StrategyTestCase.TestInstrument, 25, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 16), strat.exit_position, 29)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == 1004)

    def testShort(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-24,23.31,24.25,23.12,24.12,22446100,23.58 - exit filled
        # 2000-11-22,23.62,24.06,22.06,22.31,53317000,21.81 - exit_position
        # 2000-11-21,24.81,25.62,23.50,23.87,58651900,23.34
        # 2000-11-20,24.31,25.87,24.00,24.75,89783100,24.20
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - entry filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - enter_short_position
        
        strat.addPosEntry(datetime_from_date(2000, 11, 16), strat.enter_short_position, StrategyTestCase.TestInstrument, 29, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 22), strat.exit_position, 24)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (29 - 23.31), 2))

    def testExitOnEntryNotFilled(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - entry canceled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - exit_position
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_limit
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_limit, StrategyTestCase.TestInstrument, 5, 1, True)
        strat.addPosExit(datetime_from_date(2000, 11, 16), strat.exit_position, 29)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 0)
        self.assertTrue(strat.getEnterCanceledEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == 1000)

    def testExitTwice(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - exit filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - exit_position using a market order (cancels the previous one).
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74 - exit_position
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - entry filled
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_limit
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_limit, StrategyTestCase.TestInstrument, 25, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 14), strat.exit_position, 100)
        strat.addPosExit(datetime_from_date(2000, 11, 16), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (26.94 - 25), 2))

    def testOverwriteExit(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - exit filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - exit_position using a market order (cancels the previous one).
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23 - exit_position (cancels the previous one).
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74 - exit_position
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - entry filled
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_limit
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_limit, StrategyTestCase.TestInstrument, 25, 1, True)
        strat.addPosExit(datetime_from_date(2000, 11, 14), strat.exit_position, 100)
        strat.addPosExit(datetime_from_date(2000, 11, 15), strat.exit_position, 100)
        strat.addPosExit(datetime_from_date(2000, 11, 16), strat.exit_position)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0) # Exit cancelled events are not emitted for overwritten orders.
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (26.94 - 25), 2))

    def testExitCancelsEntry(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74 - exit_position (cancels the entry).
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - 
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_limit
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_limit, StrategyTestCase.TestInstrument, 5, 1, True)
        strat.addPosExit(datetime_from_date(2000, 11, 14), strat.exit_position, 100)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 0)
        self.assertTrue(strat.getEnterCanceledEvents() == 1)
        self.assertTrue(strat.getExitOkEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == 1000)

    def testEntryGTCExitNotGTC(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23 - GTC exit_position (never filled)
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74 - 
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - entry filled
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_limit
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_limit, StrategyTestCase.TestInstrument, 25, 1, True)
        strat.addPosExit(datetime_from_date(2000, 11, 15), strat.exit_position, 100, None, False)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 0)
        self.assertTrue(strat.getExitCanceledEvents() == 1)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 - 25, 2))

class StopPosTestCase(StrategyTestCase):
    def testLong(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - exit filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - exit_position
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - entry filled
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_stop
        
        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_stop, StrategyTestCase.TestInstrument, 25, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 16), strat.exit_position, None, 26)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (26 - 25.12), 2))

    def testShort(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-24,23.31,24.25,23.12,24.12,22446100,23.58 - exit filled
        # 2000-11-22,23.62,24.06,22.06,22.31,53317000,21.81 - exit_position
        # 2000-11-21,24.81,25.62,23.50,23.87,58651900,23.34
        # 2000-11-20,24.31,25.87,24.00,24.75,89783100,24.20
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - entry filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - enter_short_stop
        
        strat.addPosEntry(datetime_from_date(2000, 11, 16), strat.enter_short_stop, StrategyTestCase.TestInstrument, 27, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 22), strat.exit_position, None, 23)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (26.94 - 23.31), 2))

class StopLimitPosTestCase(StrategyTestCase):
    def testLong(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - exit filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - exit_position
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20 - entry filled
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87 - enter_long_stop_limit

        strat.addPosEntry(datetime_from_date(2000, 11, 10), strat.enter_long_stop_limit, StrategyTestCase.TestInstrument, 24, 25.5, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 16), strat.exit_position, 28, 27)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (28 - 24), 2))

    def testShort(self):
        strat = self.createStrategy(False, False)

        # Date,Open,High,Low,Close,Volume,Adj Close
        # 2000-11-24,23.31,24.25,23.12,24.12,22446100,23.58 - exit filled
        # 2000-11-22,23.62,24.06,22.06,22.31,53317000,21.81 - exit_position
        # 2000-11-21,24.81,25.62,23.50,23.87,58651900,23.34
        # 2000-11-20,24.31,25.87,24.00,24.75,89783100,24.20
        # 2000-11-17,26.94,29.25,25.25,28.81,59639400,28.17 - entry filled
        # 2000-11-16,28.75,29.81,27.25,27.37,37990000,26.76 - enter_short_stop_limit
        # 2000-11-15,28.81,29.44,27.70,28.87,50655200,28.23
        # 2000-11-14,27.37,28.50,26.50,28.37,77496700,27.74
        # 2000-11-13,25.12,25.87,23.50,24.75,61651900,24.20
        # 2000-11-10,26.44,26.94,24.87,25.44,54614100,24.87

        strat.addPosEntry(datetime_from_date(2000, 11, 16), strat.enter_short_stop_limit, StrategyTestCase.TestInstrument, 29, 27, 1)
        strat.addPosExit(datetime_from_date(2000, 11, 22), strat.exit_position, 25, 24)
        strat.run()

        self.assertTrue(strat.getEnterOkEvents() == 1)
        self.assertTrue(strat.getEnterCanceledEvents() == 0)
        self.assertTrue(strat.getExitOkEvents() == 1)
        self.assertTrue(strat.getExitCanceledEvents() == 0)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (29 - 24), 2))

def getTestCases(includeExternal = True):
    ret = []

    ret.append(LongPosTestCase("testLongPosition"))
    if includeExternal:
        ret.append(LongPosTestCase("testLongPosition_ExternalBF"))
        ret.append(LongPosTestCase("testLongPosition_ExternalBFAndBroker"))
    ret.append(LongPosTestCase("testLongPositionAdjClose"))
    if includeExternal:
        ret.append(LongPosTestCase("testLongPositionAdjClose_ExternalBF"))
        ret.append(LongPosTestCase("testLongPositionAdjClose_ExternalBFAndBroker"))
    ret.append(LongPosTestCase("testLongPositionGTC"))
    ret.append(LongPosTestCase("testEntryCanceled"))
    ret.append(LongPosTestCase("testIntradayExitOnClose_AllInOneDay"))
    ret.append(LongPosTestCase("testIntradayExitOnClose_EntryNotFilled"))
    ret.append(LongPosTestCase("testIntradayExitOnClose_BuyOnLastBar"))
    ret.append(LongPosTestCase("testIntradayExitOnClose_BuyOnPenultimateBar"))

    ret.append(ShortPosTestCase("testShortPosition"))
    if includeExternal:
        ret.append(ShortPosTestCase("testShortPosition_ExternalBF"))
        ret.append(ShortPosTestCase("testShortPosition_ExternalBFAndBroker"))
    ret.append(ShortPosTestCase("testShortPositionAdjClose"))
    if includeExternal:
        ret.append(ShortPosTestCase("testShortPositionAdjClose_ExternalBF"))
        ret.append(ShortPosTestCase("testShortPositionAdjClose_ExternalBFAndBroker"))
    ret.append(ShortPosTestCase("testShortPosition_exit_canceled"))
    if includeExternal:
        ret.append(ShortPosTestCase("testShortPosition_exit_canceled_ExternalBF"))
        ret.append(ShortPosTestCase("testShortPosition_exit_canceled_ExternalBFAndBroker"))
    ret.append(ShortPosTestCase("testShortPosition_exit_canceledAndReSubmitted"))
    ret.append(ShortPosTestCase("testIntradayExitOnClose"))

    ret.append(LimitPosTestCase("testLong"))
    ret.append(LimitPosTestCase("testShort"))
    ret.append(LimitPosTestCase("testExitOnEntryNotFilled"))
    ret.append(LimitPosTestCase("testExitTwice"))
    ret.append(LimitPosTestCase("testOverwriteExit"))
    ret.append(LimitPosTestCase("testExitCancelsEntry"))
    ret.append(LimitPosTestCase("testEntryGTCExitNotGTC"))

    ret.append(StopPosTestCase("testLong"))
    ret.append(StopPosTestCase("testShort"))

    ret.append(StopLimitPosTestCase("testLong"))
    ret.append(StopLimitPosTestCase("testShort"))

    ret.append(BrokerOrdersTestCase("testLimitOrder"))

    return ret

