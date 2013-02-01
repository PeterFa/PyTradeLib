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

from pytradelab import strategy
from pytradelab.barfeed import yahoofeed
from pytradelab.technical import ma
from pytradelab.technical import cross
import common

class SMACrossOverStrategy(strategy.Strategy):
    def __init__(self, feed, fastSMA, slowSMA):
        strategy.Strategy.__init__(self, feed, 1000)
        ds = feed["orcl"].get_close_data_series()
        fastSMADS = ma.SMA(ds, fastSMA)
        slowSMADS = ma.SMA(ds, slowSMA)
        self.__crossAbove = cross.CrossAbove(fastSMADS, slowSMADS)
        self.__crossBelow = cross.CrossBelow(fastSMADS, slowSMADS)
        self.__longPos = None
        self.__shortPos = None
        self.__finalValue = None

    def enter_longPosition(self, bars):
        raise Exception("Not implemented")

    def enter_shortPosition(self, bars):
        raise Exception("Not implemented")

    def exitLongPosition(self, bars, position):
        raise Exception("Not implemented")

    def exitShortPosition(self, bars, position):
        raise Exception("Not implemented")

    def getFinalValue(self):
        return self.__finalValue

    def printDebug(self, *args):
        args = [str(arg) for arg in args]
        # print " ".join(args)

    def on_enter_ok(self, position):
        self.printDebug("enterOk: ", self.get_current_date_time(), position.get_entry_order().get_execution_info().get_price(), position)

    def on_enter_canceled(self, position):
        self.printDebug("enterCanceled: ", self.get_current_date_time(), position)
        if position == self.__longPos:
            self.__longPos = None
        elif position == self.__shortPos:
            self.__shortPos = None
        else:
            assert(False)

    def on_exit_ok(self, position):
        self.printDebug("exitOk: ", self.get_current_date_time(), position.get_exit_order().get_execution_info().get_price(), position)
        if position == self.__longPos:
            self.__longPos = None
        elif position == self.__shortPos:
            self.__shortPos = None
        else:
            assert(False)

    def on_exit_canceled(self, position):
        self.printDebug("exitCanceled: ", self.get_current_date_time(), position, ". Resubmitting as a Market order.")
        # If the exit was canceled, re-submit it.
        self.exit_position(position)

    def on_bars(self, bars):
        bar = bars.get_bar("orcl")
        self.printDebug("%s: O=%s H=%s L=%s C=%s" % (bar.get_date_time(), bar.get_open(), bar.get_high(), bar.get_low(), bar.get_close()))

        # Wait for enough bars to be available.
        if self.__crossAbove[-1] is None or self.__crossBelow[-1] is None:
            return

        if self.__crossAbove[-1] == 1:
            if self.__shortPos:
                self.exitShortPosition(bars, self.__shortPos)
            assert(self.__longPos == None)
            self.__longPos = self.enter_longPosition(bars)
        elif self.__crossBelow[-1] == 1:
            if self.__longPos:
                self.exitLongPosition(bars, self.__longPos)
            assert(self.__shortPos == None)
            self.__shortPos = self.enter_shortPosition(bars)

    def on_finish(self, bars):
        self.__finalValue = self.get_broker().get_value(bars)

class MarketOrderStrategy(SMACrossOverStrategy):
    def enter_longPosition(self, bars):
        return self.enter_long("orcl", 10)

    def enter_shortPosition(self, bars):
        return self.enter_short("orcl", 10)

    def exitLongPosition(self, bars, position):
        self.exit_position(position)

    def exitShortPosition(self, bars, position):
        self.exit_position(position)

class LimitOrderStrategy(SMACrossOverStrategy):
    def __getMiddlePrice(self, bars):
        bar = bars.get_bar("orcl")
        ret = bar.get_low() + (bar.get_high() - bar.get_low()) / 2.0
        ret = round(ret, 2)
        return ret

    def enter_longPosition(self, bars):
        price = self.__getMiddlePrice(bars)
        ret = self.enter_long_limit("orcl", price, 10)
        self.printDebug("enter_long:", self.get_current_date_time(), price, ret)
        return ret

    def enter_shortPosition(self, bars):
        price = self.__getMiddlePrice(bars)
        ret = self.enter_short_position("orcl", price, 10)
        self.printDebug("enter_short:", self.get_current_date_time(), price, ret)
        return ret

    def exitLongPosition(self, bars, position):
        price = self.__getMiddlePrice(bars)
        self.printDebug("exitLong:", self.get_current_date_time(), price, position)
        self.exit_position(position, price)

    def exitShortPosition(self, bars, position):
        price = self.__getMiddlePrice(bars)
        self.printDebug("exitShort:", self.get_current_date_time(), price, position)
        self.exit_position(position, price)

class TestSMACrossOver(unittest.TestCase):
    def __test(self, strategy_class, finalValue):
        feed = yahoofeed.Feed()
        feed.add_bars_from_csv("orcl", common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        myStrategy = strategy_class(feed, 10, 25)
        myStrategy.run()
        myStrategy.printDebug("Final result:", round(myStrategy.getFinalValue(), 2))
        self.assertTrue(round(myStrategy.getFinalValue(), 2) == finalValue)

    def testWithMarketOrder(self):
        # This is the exact same result that we get using NinjaTrader.
        self.__test(MarketOrderStrategy, 1000 - 22.7)

    def testWithLimitOrder(self):
        # The result is different than the one we get using NinjaTrader. NinjaTrader processes Limit orders in a different way.
        self.__test(LimitOrderStrategy, 1000 + 32.7)

def getTestCases():
    ret = []
    ret.append(TestSMACrossOver("testWithMarketOrder"))
    ret.append(TestSMACrossOver("testWithLimitOrder"))
    return ret

