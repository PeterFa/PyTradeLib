# PyAlgoTrade
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

from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.broker import backtesting
from pyalgotrade import broker

import strategy_test
import common

import unittest

class SharpeRatioTestCase(unittest.TestCase):
    def testNoTrades(self):
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        strat = strategy_test.TestStrategy(bar_feed, 1000)
        stratAnalyzer = sharpe.SharpeRatio()
        strat.attach_analyzer(stratAnalyzer)

        strat.run()
        self.assertTrue(strat.get_broker().get_cash() == 1000)
        self.assertTrue(stratAnalyzer.get_sharpe_ratio(0.04, 252, annualized=True) == 0)
        self.assertTrue(stratAnalyzer.get_sharpe_ratio(0, 252) == 0)
        self.assertTrue(stratAnalyzer.get_sharpe_ratio(0, 252, annualized=True) == 0)

    def __testIGE_BrokerImpl(self, quantity):
        initialCash = 42.09 * quantity
        # This testcase is based on an example from Ernie Chan's book:
        # 'Quantitative Trading: How to Build Your Own Algorithmic Trading Business'
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)
        strat.get_broker().set_use_adj_values(True)
        strat.setBrokerOrdersGTC(True)
        stratAnalyzer = sharpe.SharpeRatio()
        strat.attach_analyzer(stratAnalyzer)

        # Manually place the order to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, "ige", quantity, True) # Adj. Close: 42.09
        order.set_good_until_canceled(True)
        strat.get_broker().place_order(order)
        strat.addOrder(strategy_test.datetime_from_date(2007, 11, 13), strat.get_broker().create_market_order, broker.Order.Action.SELL, "ige", quantity, True) # Adj. Close: 127.64
        strat.run()
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == initialCash + (127.64 - 42.09) * quantity)
        self.assertTrue(strat.get_order_updated_events() == 2)
        # The results are slightly different only because I'm taking into account the first bar as well.
        self.assertTrue(round(stratAnalyzer.get_sharpe_ratio(0.04, 252, annualized=True), 4) == 0.7889)

    def testIGE_Broker(self):
        self.__testIGE_BrokerImpl(1)

    def testIGE_Broker2(self):
        self.__testIGE_BrokerImpl(2)

    def testIGE_BrokerWithCommission(self):
        commision = 0.5
        initialCash = 42.09 + commision
        # This testcase is based on an example from Ernie Chan's book:
        # 'Quantitative Trading: How to Build Your Own Algorithmic Trading Business'
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        brk = backtesting.Broker(initialCash, bar_feed, backtesting.FixedCommission(commision))
        strat = strategy_test.TestStrategy(bar_feed, initialCash, brk)
        strat.get_broker().set_use_adj_values(True)
        strat.setBrokerOrdersGTC(True)
        stratAnalyzer = sharpe.SharpeRatio()
        strat.attach_analyzer(stratAnalyzer)

        # Manually place the order to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, "ige", 1, True) # Adj. Close: 42.09
        order.set_good_until_canceled(True)
        strat.get_broker().place_order(order)
        strat.addOrder(strategy_test.datetime_from_date(2007, 11, 13), strat.get_broker().create_market_order, broker.Order.Action.SELL, "ige", 1, True) # Adj. Close: 127.64
        strat.run()
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == initialCash + (127.64 - 42.09 - commision*2))
        self.assertTrue(strat.get_order_updated_events() == 2)
        # The results are slightly different only because I'm taking into account the first bar as well,
        # and I'm also adding commissions.
        self.assertEqual(round(stratAnalyzer.get_sharpe_ratio(0.04, 252, annualized=True), 6), 0.776443)

    def testSharpeRatioIGE_SPY_Broker(self):
        initialCash = 42.09
        # This testcase is based on an example from Ernie Chan's book:
        # 'Quantitative Trading: How to Build Your Own Algorithmic Trading Business'
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv("ige", common.get_data_file_path("sharpe-ratio-test-ige.csv"))
        bar_feed.add_bars_from_csv("spy", common.get_data_file_path("sharpe-ratio-test-spy.csv"))
        strat = strategy_test.TestStrategy(bar_feed, initialCash)
        strat.get_broker().set_use_adj_values(True)
        strat.setBrokerOrdersGTC(True)
        stratAnalyzer = sharpe.SharpeRatio()
        strat.attach_analyzer(stratAnalyzer)

        # Manually place IGE order to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.BUY, "ige", 1, True) # Adj. Close: 42.09
        order.set_good_until_canceled(True)
        strat.get_broker().place_order(order)

        # Manually place SPY order to get it filled on the first bar.
        order = strat.get_broker().create_market_order(broker.Order.Action.SELL_SHORT, "spy", 1, True) # Adj. Close: 105.52
        order.set_good_until_canceled(True)
        strat.get_broker().place_order(order)

        strat.addOrder(strategy_test.datetime_from_date(2007, 11, 13), strat.get_broker().create_market_order, broker.Order.Action.SELL, "ige", 1, True) # Adj. Close: 127.64
        strat.addOrder(strategy_test.datetime_from_date(2007, 11, 13), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, "spy", 1, True) # Adj. Close: 147.67

        strat.run()
        self.assertTrue(strat.get_order_updated_events() == 4)
        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(initialCash + (127.64 - 42.09) + (105.52 - 147.67), 2))
        # TODO: The results are different from the ones in the book. Analyze why.
        # self.assertTrue(round(stratAnalyzer.get_sharpe_ratio(0, 252), 5) == 0.92742)

def getTestCases():
    ret = []

    ret.append(SharpeRatioTestCase("testNoTrades"))
    ret.append(SharpeRatioTestCase("testIGE_Broker"))
    ret.append(SharpeRatioTestCase("testIGE_Broker2"))
    ret.append(SharpeRatioTestCase("testIGE_BrokerWithCommission"))
    ret.append(SharpeRatioTestCase("testSharpeRatioIGE_SPY_Broker"))

    return ret

