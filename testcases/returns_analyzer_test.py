# This file was originally part of PyAlgoTrade.
#
# Copyright 2012 Gabriel Martin Becedillas Ruiz
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

from pytradelib.barfeed import yahoofeed
from pytradelib.barfeed import csvfeed
from pytradelib.stratanalyzer import returns
from pytradelib import broker

import strategy_test
import common

import unittest

class PosTrackerTestCase(unittest.TestCase):
    invalid_price = 5000

    def testBuyAndSellBreakEvenWithCommission(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10, 0.01)
        position_tracker.sell(1, 10.02, 0.01)
        self.assertTrue(position_tracker.get_cost() == 10)
        # We need to round here or else the testcase fails since the value returned is not exactly 0.<
        # The same issue can be reproduced with this piece of code:
        # a = 10.02 - 10
        # b = 0.02
        # print a - b
        # print a - b == 0
        self.assertTrue(round(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price), 2) == 0.0)
        self.assertTrue(round(position_tracker.get_return(PosTrackerTestCase.invalid_price), 2) == 0.0)

    def testBuyAndSellBreakEven(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10)
        position_tracker.sell(1, 10)
        self.assertTrue(position_tracker.get_cost() == 10)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 0)
        self.assertTrue(position_tracker.get_return(PosTrackerTestCase.invalid_price) == 0)

    def testBuyAndSellWin(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10)
        position_tracker.sell(1, 11)
        self.assertTrue(position_tracker.get_cost() == 10)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 1)
        self.assertTrue(position_tracker.get_return(PosTrackerTestCase.invalid_price) == 0.1)

    def testBuyAndSellMultipleEvals(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(2, 10)
        self.assertTrue(position_tracker.get_cost() == 20)
        self.assertTrue(position_tracker.get_net_profit(10) == 0)
        self.assertTrue(position_tracker.get_return(10) == 0)

        self.assertTrue(position_tracker.get_net_profit(11) == 2)
        self.assertTrue(position_tracker.get_return(11) == 0.1)

        self.assertTrue(position_tracker.get_net_profit(20) == 20)
        self.assertTrue(position_tracker.get_return(20) == 1)

        position_tracker.sell(1, 11)
        self.assertTrue(position_tracker.get_cost() == 20)
        self.assertTrue(position_tracker.get_net_profit(11) == 2)
        self.assertTrue(position_tracker.get_return(11) == 0.1)

        position_tracker.sell(1, 10)
        self.assertTrue(position_tracker.get_cost() == 20)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 1)
        self.assertTrue(position_tracker.get_return(11) == 0.05)

    def testSellAndBuyWin(self):
        position_tracker = returns.PositionTracker()
        position_tracker.sell(1, 11)
        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 11)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 1)
        self.assertTrue(round(position_tracker.get_return(PosTrackerTestCase.invalid_price), 4) == round(0.090909091, 4))

    def testSellAndBuyMultipleEvals(self):
        position_tracker = returns.PositionTracker()
        position_tracker.sell(2, 11)
        self.assertTrue(position_tracker.get_cost() == 22)
        self.assertTrue(position_tracker.get_net_profit(11) == 0)
        self.assertTrue(position_tracker.get_return(11) == 0)

        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 22)
        self.assertTrue(position_tracker.get_net_profit(11) == 1)
        self.assertTrue(round(position_tracker.get_return(11), 4) == round(0.045454545, 4))

        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 22)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 2)
        self.assertTrue(round(position_tracker.get_return(PosTrackerTestCase.invalid_price), 4) == round(0.090909091, 4))

    def testBuySellBuy(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 10)

        position_tracker.sell(2, 13) # Short selling 1 @ $13
        self.assertTrue(position_tracker.get_cost() == 10 + 13)

        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 10 + 13)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 6)
        self.assertTrue(round(position_tracker.get_return(PosTrackerTestCase.invalid_price), 4) == round(0.260869565, 4))

    def testBuyAndUpdate(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 10)
        self.assertTrue(position_tracker.get_net_profit(20) == 10)
        self.assertTrue(position_tracker.get_return(20) == 1)

        position_tracker.update(15)
        self.assertTrue(position_tracker.get_cost() == 15)
        self.assertTrue(position_tracker.get_net_profit(15) == 0)
        self.assertTrue(position_tracker.get_return(15) == 0)

        self.assertTrue(position_tracker.get_net_profit(20) == 5)
        self.assertTrue(round(position_tracker.get_return(20), 2) == 0.33)

    def testBuyUpdateAndSell(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10)
        self.assertTrue(position_tracker.get_cost() == 10)
        self.assertTrue(position_tracker.get_net_profit(15) == 5)
        self.assertTrue(position_tracker.get_return(15) == 0.5)

        position_tracker.update(15)
        self.assertTrue(position_tracker.get_cost() == 15)
        position_tracker.sell(1, 20)
        self.assertTrue(position_tracker.get_cost() == 15)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 5)
        self.assertTrue(round(position_tracker.get_return(PosTrackerTestCase.invalid_price), 2) == 0.33)

        position_tracker.update(100)
        self.assertTrue(position_tracker.get_cost() == 0)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price) == 0)
        self.assertTrue(position_tracker.get_return(PosTrackerTestCase.invalid_price) == 0)

    def testBuyAndSellBreakEvenWithCommision(self):
        position_tracker = returns.PositionTracker()
        position_tracker.buy(1, 10, 0.5)
        position_tracker.sell(1, 11, 0.5)
        self.assertTrue(position_tracker.get_cost() == 10)
        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price, False) == 1)
        self.assertTrue(position_tracker.get_return(PosTrackerTestCase.invalid_price, False) == 0.1)

        self.assertTrue(position_tracker.get_net_profit(PosTrackerTestCase.invalid_price, True) == 0)
        self.assertTrue(position_tracker.get_return(PosTrackerTestCase.invalid_price, True) == 0)

    def testLongShortEqualAmount(self):
        position_trackerXYZ = returns.PositionTracker()
        position_trackerXYZ.buy(11, 10)
        position_trackerXYZ.sell(11, 30)
        self.assertTrue(position_trackerXYZ.get_cost() == 11*10)
        self.assertTrue(position_trackerXYZ.get_net_profit(PosTrackerTestCase.invalid_price) == 20*11)
        self.assertTrue(position_trackerXYZ.get_return(PosTrackerTestCase.invalid_price) == 2)

        position_trackerABC = returns.PositionTracker()
        position_trackerABC.sell(100, 1.1)
        position_trackerABC.buy(100, 1)
        self.assertTrue(position_trackerABC.get_cost() == 100*1.1)
        self.assertTrue(round(position_trackerABC.get_net_profit(PosTrackerTestCase.invalid_price), 2) == 100*0.1)
        self.assertEqual(round(position_trackerABC.get_return(PosTrackerTestCase.invalid_price), 2), 0.09)

        combinedCost = position_trackerXYZ.get_cost() + position_trackerABC.get_cost()
        combinedPL = position_trackerXYZ.get_net_profit(PosTrackerTestCase.invalid_price) + position_trackerABC.get_net_profit(PosTrackerTestCase.invalid_price)
        combinedReturn = combinedPL / float(combinedCost)
        self.assertTrue(round(combinedReturn, 9) == 1.045454545)

class ReturnsTestCase(unittest.TestCase):
    TestInstrument = "any"
    
    def testOneBarReturn(self):
        initialCash = 1000
        bar_feed = yahoofeed.Feed()
        bar_feed.set_bar_filter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 07), strategy_test.datetime_from_date(2001, 12, 07)))
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)

        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the orders to get them filled on the first (and only) bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.74
        strat.get_broker().place_order(order)
        order = strat.get_broker().create_market_order(broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.91
        strat.get_broker().place_order(order)

        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        self.assertTrue(strat.get_broker().get_cash() == initialCash + (15.91 - 15.74))

        finalValue = 1000 - 15.74 + 15.91
        rets = (finalValue - initialCash) / float(initialCash)
        self.assertEqual(stratAnalyzer.get_returns()[-1], rets)

    def testTwoBarReturns_OpenOpen(self):
        initialCash = 15.61
        bar_feed = yahoofeed.Feed()
        bar_feed.set_bar_filter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.61
        strat.get_broker().place_order(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.get_broker().create_market_order, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.74

        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        self.assertTrue(strat.get_broker().get_cash() == initialCash + (15.74 - 15.61))
        # First day returns: Open vs Close
        self.assertTrue(stratAnalyzer.get_returns()[0] == (15.90 - 15.61) / 15.61)
        # Second day returns: Open vs Prev. day's close
        self.assertTrue(stratAnalyzer.get_returns()[1] == (15.74 - 15.90) / 15.90)

    def testTwoBarReturns_OpenClose(self):
        initialCash = 15.61
        bar_feed = yahoofeed.Feed()
        bar_feed.set_bar_filter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.61
        strat.get_broker().place_order(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.get_broker().create_market_order, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.91

        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        self.assertTrue(strat.get_broker().get_cash() == initialCash + (15.91 - 15.61))
        # First day returns: Open vs Close
        self.assertTrue(stratAnalyzer.get_returns()[0] == (15.90 - 15.61) / 15.61)
        # Second day returns: Close vs Prev. day's close
        self.assertTrue(stratAnalyzer.get_returns()[1] == (15.91 - 15.90) / 15.90)

    def testTwoBarReturns_CloseOpen(self):
        initialCash = 15.9
        bar_feed = yahoofeed.Feed()
        bar_feed.set_bar_filter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.90
        strat.get_broker().place_order(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.get_broker().create_market_order, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, False) # Open: 15.74

        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        self.assertTrue(strat.get_broker().get_cash() == initialCash + (15.74 - 15.90))
        # First day returns: 0
        self.assertTrue(stratAnalyzer.get_returns()[0] == 0)
        # Second day returns: Open vs Prev. day's close
        self.assertTrue(stratAnalyzer.get_returns()[1] == (15.74 - 15.90) / 15.90)

    def testTwoBarReturns_CloseClose(self):
        initialCash = 15.90
        bar_feed = yahoofeed.Feed()
        bar_feed.set_bar_filter(csvfeed.DateRangeFilter(strategy_test.datetime_from_date(2001, 12, 06), strategy_test.datetime_from_date(2001, 12, 07)))
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)

        # 2001-12-06,15.61,16.03,15.50,15.90,66944900,15.55
        # 2001-12-07,15.74,15.95,15.55,15.91,42463200,15.56
        # Manually place the entry order, to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.90
        strat.get_broker().place_order(order)
        strat.addOrder(strategy_test.datetime_from_date(2001, 12, 06), strat.get_broker().create_market_order, broker.Order.Action.SELL, ReturnsTestCase.TestInstrument, 1, True) # Close: 15.91

        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        self.assertTrue(strat.get_broker().get_cash() == initialCash + (15.91 - 15.90))
        # First day returns: 0
        self.assertTrue(stratAnalyzer.get_returns()[0] == 0)
        # Second day returns: Open vs Prev. day's close
        self.assertTrue(stratAnalyzer.get_returns()[1] == (15.91 - 15.90) / 15.90)

    def testCumulativeReturn(self):
        initialCash = 33.06
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)

        strat.addPosEntry(strategy_test.datetime_from_date(2001, 1, 12), strat.enter_long, ReturnsTestCase.TestInstrument, 1) # 33.06
        strat.addPosExit(strategy_test.datetime_from_date(2001, 11, 27), strat.exit_position) # 14.32
    
        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(initialCash + (14.32 - 33.06), 2))
        self.assertTrue(round(33.06 * (1 + stratAnalyzer.get_cumulative_returns()[-1]), 2) == 14.32)

    def testGoogle2011(self):
        initial_value = 1000000
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv(ReturnsTestCase.TestInstrument, common.get_data_file_path("goog-2011-yahoofinance.csv"))

        strat = strategy_test.TestStrategy(bar_feed, initial_value)
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, ReturnsTestCase.TestInstrument, 1654, True) # 2011-01-03 close: 604.35
        strat.get_broker().place_order(order)

        stratAnalyzer = returns.Returns()
        strat.attach_analyzer(stratAnalyzer)
        strat.run()
        finalValue = strat.get_broker().get_value(strat.get_feed().get_last_bars())

        self.assertEqual(round(stratAnalyzer.get_cumulative_returns()[-1], 4), round((finalValue - initial_value) / float(initial_value), 4))

def getTestCases():
    ret = []

    ret.append(PosTrackerTestCase("testBuyAndSellBreakEven"))
    ret.append(PosTrackerTestCase("testBuyAndSellBreakEvenWithCommission"))
    ret.append(PosTrackerTestCase("testBuyAndSellWin"))
    ret.append(PosTrackerTestCase("testBuyAndSellMultipleEvals"))
    ret.append(PosTrackerTestCase("testSellAndBuyWin"))
    ret.append(PosTrackerTestCase("testSellAndBuyMultipleEvals"))
    ret.append(PosTrackerTestCase("testBuySellBuy"))
    ret.append(PosTrackerTestCase("testBuyAndUpdate"))
    ret.append(PosTrackerTestCase("testBuyUpdateAndSell"))
    ret.append(PosTrackerTestCase("testBuyAndSellBreakEvenWithCommision"))
    ret.append(PosTrackerTestCase("testLongShortEqualAmount"))

    ret.append(ReturnsTestCase("testOneBarReturn"))
    ret.append(ReturnsTestCase("testTwoBarReturns_OpenOpen"))
    ret.append(ReturnsTestCase("testTwoBarReturns_OpenClose"))
    ret.append(ReturnsTestCase("testTwoBarReturns_CloseOpen"))
    ret.append(ReturnsTestCase("testTwoBarReturns_CloseClose"))
    ret.append(ReturnsTestCase("testCumulativeReturn"))
    ret.append(ReturnsTestCase("testGoogle2011"))

    return ret

