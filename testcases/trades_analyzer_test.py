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

from pyalgotrade.barfeed import ninjatraderfeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade.stratanalyzer import trades
from pyalgotrade import broker
from pyalgotrade.broker import backtesting

import strategy_test
import common

import unittest
import datetime
import math
from distutils import version
import pytz
import numpy

def buildUTCDateTime(year, month, day, hour, minute):
    ret = datetime.datetime(year, month, day, hour, minute)
    ret = pytz.utc.localize(ret)
    return ret

class TradesAnalyzerTestCase(unittest.TestCase):
    TestInstrument = "spy"

    def __createStrategy(self):
        bar_feed = ninjatraderfeed.Feed(ninjatraderfeed.Frequency.MINUTE)
        bar_filter = csvfeed.USEquitiesRTH()
        bar_feed.set_bar_filter(bar_filter)
        bar_feed.add_bars_from_csv(TradesAnalyzerTestCase.TestInstrument, common.get_data_file_path("nt-spy-minute-2011.csv"))
        return strategy_test.TestStrategy(bar_feed, 1000)

    def testNoTrades(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        strat.run()

        self.assertTrue(strat.get_broker().get_cash() == 1000)

        self.assertTrue(stratAnalyzer.get_count() == 0)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)
        self.assertTrue(stratAnalyzer.get_profitable_count() == 0)
        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 0)

    def testSomeTrades_Position(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Winning trade
        strat.addPosEntry(buildUTCDateTime(2011, 1, 3, 15, 0), strat.enter_long, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        strat.addPosExit(buildUTCDateTime(2011, 1, 3, 15, 16), strat.exit_position) # 127.16
        # Losing trade
        strat.addPosEntry(buildUTCDateTime(2011, 1, 3, 15, 30), strat.enter_long, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.addPosExit(buildUTCDateTime(2011, 1, 3, 15, 31), strat.exit_position) # 127.16
        # Winning trade
        strat.addPosEntry(buildUTCDateTime(2011, 1, 3, 15, 38), strat.enter_long, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        strat.addPosExit(buildUTCDateTime(2011, 1, 3, 15, 42), strat.exit_position) # 127.26
        # Unfinished trade not closed
        strat.addPosEntry(buildUTCDateTime(2011, 1, 3, 15, 47), strat.enter_long, TradesAnalyzerTestCase.TestInstrument, 1) # 127.34
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.16 - 127.14) + (127.16 - 127.2) + (127.26 - 127.16) - 127.34, 2))

        self.assertTrue(stratAnalyzer.get_count() == 3)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)
        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == 0.03)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=1), 2) == 0.07)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=0), 2) == 0.06)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 2)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.06)
        self.assertTrue(round(stratAnalyzer.get_profits().std(ddof=1), 2) == 0.06)
        self.assertTrue(round(stratAnalyzer.get_profits().std(ddof=0), 2) == 0.04)
        self.assertEqual(stratAnalyzer.get_positive_returns()[0], (127.16 - 127.14) / 127.14)
        self.assertEqual(stratAnalyzer.get_positive_returns()[1], (127.26 - 127.16) / 127.16)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.04)
        if version.LooseVersion(numpy.__version__) >= version.LooseVersion("1.6.2"):
            self.assertTrue(math.isnan(stratAnalyzer.get_losses().std(ddof=1)))
        else:
            self.assertTrue(stratAnalyzer.get_losses().std(ddof=1) == 0)
        self.assertTrue(stratAnalyzer.get_losses().std(ddof=0) == 0)
        self.assertEqual(stratAnalyzer.get_negative_returns()[0], (127.16 - 127.2) / 127.2)

    def testSomeTrades(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Winning trade
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Losing trade
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 31), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Winning trade
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 38), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 42), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.26
        # Open trade.
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 47), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.34
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.16 - 127.14) + (127.16 - 127.2) + (127.26 - 127.16) - 127.34, 2))

        self.assertTrue(stratAnalyzer.get_count() == 3)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)
        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == 0.03)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=1), 2) == 0.07)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=0), 2) == 0.06)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 2)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.06)
        self.assertTrue(round(stratAnalyzer.get_profits().std(ddof=1), 2) == 0.06)
        self.assertTrue(round(stratAnalyzer.get_profits().std(ddof=0), 2) == 0.04)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.04)
        if version.LooseVersion(numpy.__version__) >= version.LooseVersion("1.6.2"):
            self.assertTrue(math.isnan(stratAnalyzer.get_losses().std(ddof=1)))
        else:
            self.assertTrue(stratAnalyzer.get_losses().std(ddof=1) == 0)
        self.assertTrue(stratAnalyzer.get_losses().std(ddof=0) == 0)

    def testSomeTradesWithCommissions(self):
        strat = self.__createStrategy()
        strat.get_broker().set_commission(backtesting.FixedCommission(0.01))
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Losing trade
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 31), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Winning trade
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 38), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 42), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.26
        # Open trade.
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 47), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.34
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.16 - 127.2) + (127.26 - 127.16) - 127.34 - 0.01*5, 2))
        self.assertTrue(numpy.array_equal(stratAnalyzer.get_commissions_for_all_trades(), numpy.array([0.02, 0.02])))
        self.assertTrue(numpy.array_equal(stratAnalyzer.get_commissions_for_profitable_trades(), numpy.array([0.02])))
        self.assertTrue(numpy.array_equal(stratAnalyzer.get_commissions_for_unprofitable_trades(), numpy.array([0.02])))
        self.assertTrue(numpy.array_equal(stratAnalyzer.get_commissions_for_even_trades(), numpy.array([])))

    def testLongShort(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        # Exit long and enter short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 2) # 127.16
        # Exit short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.16 - 127.14) + (127.16 - 127.2), 2))

        self.assertTrue(stratAnalyzer.get_count() == 2)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == -0.01)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=1), 4) == 0.0424)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.02)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.04)

    def testLongShort2(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        # Exit long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Enter short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.SELL_SHORT, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Exit short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.16 - 127.14) + (127.16 - 127.2), 2))

        self.assertTrue(stratAnalyzer.get_count() == 2)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == -0.01)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=1), 4) == 0.0424)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.02)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.04)

    def testShortLong(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.SELL_SHORT, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        # Exit short and enter long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 2) # 127.16
        # Exit long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.14 - 127.16) + (127.2 - 127.16), 2))

        self.assertTrue(stratAnalyzer.get_count() == 2)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == 0.01)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=1), 4) == 0.0424)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.04)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.02)

    def testShortLong2(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.SELL_SHORT, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        # Exit short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Enter long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Exit long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.14 - 127.16) + (127.2 - 127.16), 2))

        self.assertTrue(stratAnalyzer.get_count() == 2)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == 0.01)
        self.assertTrue(round(stratAnalyzer.get_all().std(ddof=1), 4) == 0.0424)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.04)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.02)

    def testLong2(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        # Extend long position
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Exit long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 2) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.2 - 127.14) + (127.2 - 127.16), 2))

        self.assertTrue(stratAnalyzer.get_count() == 1)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == 0.1)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.1)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 0)

    def testLong3(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.BUY, TradesAnalyzerTestCase.TestInstrument, 2) # 127.14
        # Decrease long position
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Exit long
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.SELL, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.2 - 127.14) + (127.16 - 127.14), 2))

        self.assertTrue(stratAnalyzer.get_count() == 1)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == 0.08)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_profits().mean(), 2) == 0.08)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 0)

    def testShort2(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.SELL_SHORT, TradesAnalyzerTestCase.TestInstrument, 1) # 127.14
        # Extend short position
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.SELL_SHORT, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Exit short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 2) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.14 - 127.2) + (127.16 - 127.2), 2))

        self.assertTrue(stratAnalyzer.get_count() == 1)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == -0.1)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.1)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 0)

    def testShort3(self):
        strat = self.__createStrategy()
        stratAnalyzer = trades.Trades()
        strat.attach_analyzer(stratAnalyzer)

        # Enter short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 0), strat.get_broker().create_market_order, broker.Order.Action.SELL_SHORT, TradesAnalyzerTestCase.TestInstrument, 2) # 127.14
        # Decrease short position
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 16), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 1) # 127.16
        # Exit short
        strat.addOrder(buildUTCDateTime(2011, 1, 3, 15, 30), strat.get_broker().create_market_order, broker.Order.Action.BUY_TO_COVER, TradesAnalyzerTestCase.TestInstrument, 1) # 127.2
        strat.run()

        self.assertTrue(round(strat.get_broker().get_cash(), 2) == round(1000 + (127.14 - 127.16) + (127.14 - 127.2), 2))

        self.assertTrue(stratAnalyzer.get_count() == 1)
        self.assertTrue(stratAnalyzer.get_even_count() == 0)

        self.assertTrue(round(stratAnalyzer.get_all().mean(), 2) == -0.08)

        self.assertTrue(stratAnalyzer.get_unprofitable_count() == 1)
        self.assertTrue(round(stratAnalyzer.get_losses().mean(), 2) == -0.08)

        self.assertTrue(stratAnalyzer.get_profitable_count() == 0)

def getTestCases():
    ret = []

    ret.append(TradesAnalyzerTestCase("testNoTrades"))
    ret.append(TradesAnalyzerTestCase("testSomeTrades_Position"))
    ret.append(TradesAnalyzerTestCase("testSomeTrades"))
    ret.append(TradesAnalyzerTestCase("testSomeTradesWithCommissions"))
    ret.append(TradesAnalyzerTestCase("testLong2"))
    ret.append(TradesAnalyzerTestCase("testLong3"))
    ret.append(TradesAnalyzerTestCase("testLongShort"))
    ret.append(TradesAnalyzerTestCase("testLongShort2"))
    ret.append(TradesAnalyzerTestCase("testShort2"))
    ret.append(TradesAnalyzerTestCase("testShort3"))
    ret.append(TradesAnalyzerTestCase("testShortLong"))
    ret.append(TradesAnalyzerTestCase("testShortLong2"))

    return ret

