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

from pytradelab import broker
from pytradelab.broker import backtesting
from pytradelab import bar
from pytradelab import barfeed

class Callback:
    def __init__(self):
        self.eventCount = 0

    def on_order_updated(self, broker_, order):
        self.eventCount += 1

class BaseTestCase(unittest.TestCase):
    TestInstrument = "orcl"

    def setUp(self):
        self.__currMinutes = 0
        self.__nextDateTime = datetime.datetime(2011, 1, 2)

    def __getNextDateTime(self, switchDay):
        if switchDay:
            self.__nextDateTime = self.__nextDateTime + datetime.timedelta(days=1)
            self.__currMinutes = 0
        else:
            self.__currMinutes += 1
        return self.__nextDateTime + datetime.timedelta(minutes=self.__currMinutes)

    def buildBars(self, openPrice, highPrice, lowPrice, closePrice, session_close = False):
        ret = {}
        date_time = self.__getNextDateTime(session_close)
        bar_ = bar.Bar(date_time, openPrice, highPrice, lowPrice, closePrice, closePrice*10, closePrice)
        bar_.set_session_close(session_close)
        ret[BaseTestCase.TestInstrument] = bar_
        return bar.Bars(ret)

class BrokerTestCase(BaseTestCase):
    def testRegressionGetActiveOrders(self):
        active_orders = []

        def on_order_updated(broker, order):
            active_orders.append(len(broker.get_active_orders()))

        brk = backtesting.Broker(1000, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))
        brk.get_order_updated_event().subscribe(on_order_updated)
        brk.place_order(brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1))
        brk.place_order(brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1))
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertEqual(brk.get_cash(), 1000 - 10*2)
        self.assertEqual(active_orders[0], 1)
        self.assertEqual(active_orders[1], 0)

class MarketOrderTestCase(BaseTestCase):
    def testBuyAndSell(self):
        brk = backtesting.Broker(11, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 1)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Sell
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 11)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testFailToBuy(self):
        brk = backtesting.Broker(5, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)

        # Fail to buy. No money.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_accepted())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 0)

        # Fail to buy. No money. Canceled due to session close.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.on_bars(self.buildBars(11, 15, 8, 12, True))
        self.assertTrue(order.is_canceled())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testBuy_GTC(self):
        brk = backtesting.Broker(5, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        order.set_good_until_canceled(True)

        # Fail to buy. No money.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.place_order(order)
        # Set session_close to true test that the order doesn't get canceled.
        brk.on_bars(self.buildBars(10, 15, 8, 12, True))
        self.assertTrue(order.is_accepted())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 0)

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.on_bars(self.buildBars(2, 15, 1, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 2)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 3)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

    def testBuyAndSellInTwoSteps(self):
        brk = backtesting.Broker(20.4, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 2)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(round(brk.get_cash(), 1) == 0.4)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 2)

        # Sell
        order = brk.create_market_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(round(brk.get_cash(), 1) == 10.4)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)

        # Sell again
        order = brk.create_market_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(11, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 11)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(round(brk.get_cash(), 1) == 21.4)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)

    def testPortfolioValue(self):
        brk = backtesting.Broker(11, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 1)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)

        self.assertTrue(brk.get_equity_with_bars(self.buildBars(11, 11, 11, 11)) == 11 + 1)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(1, 1, 1, 1)) == 1 + 1)

    def testBuyWithCommission(self):
        brk = backtesting.Broker(1020, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE), commission=backtesting.FixedCommission(10))

        # Buy
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 100)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 10)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 100)

    def testSellShort_1(self):
        brk = backtesting.Broker(1000, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Short sell
        order = brk.create_market_order(broker.Order.Action.SELL_SHORT, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(200, 200, 200, 200))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 1200)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(100, 100, 100, 100)) == 1000 + 100)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(0, 0, 0, 0)) == 1000 + 200)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(30, 30, 30, 30)) == 1000 + 170)

        # Buy at the same price.
        order = brk.create_market_order(broker.Order.Action.BUY_TO_COVER, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(200, 200, 200, 200))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 1000)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)

    def testSellShort_2(self):
        brk = backtesting.Broker(1000, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Short sell 1
        order = brk.create_market_order(broker.Order.Action.SELL_SHORT, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(100, 100, 100, 100))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(brk.get_cash() == 1100)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(100, 100, 100, 100)) == 1000)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(0, 0, 0, 0)) == 1000 + 100)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(70, 70, 70, 70)) == 1000 + 30)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(200, 200, 200, 200)) == 1000 - 100)

        # Buy 2 and earn 50
        order = brk.create_market_order(broker.Order.Action.BUY_TO_COVER, BaseTestCase.TestInstrument, 2)
        brk.place_order(order)
        brk.on_bars(self.buildBars(50, 50, 50, 50))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(brk.get_cash() == 1000) # +50 from short sell operation, -50 from buy operation.
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(50, 50, 50, 50)) == 1000 + 50)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(70, 70, 70, 70)) == 1000 + 50 + 20)

        # Sell 1 and earn 50
        order = brk.create_market_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(100, 100, 100, 100))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(brk.get_equity_with_bars(self.buildBars(70, 70, 70, 70)) == 1000 + 50 + 50)

    def testSellShort_3(self):
        brk = backtesting.Broker(100, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy 1
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(100, 100, 100, 100))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(brk.get_cash() == 0)

        # Sell 2
        order = brk.create_market_order(broker.Order.Action.SELL_SHORT, BaseTestCase.TestInstrument, 2)
        brk.place_order(order)
        brk.on_bars(self.buildBars(100, 100, 100, 100))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(brk.get_cash() == 200)

        # Buy 1
        order = brk.create_market_order(broker.Order.Action.BUY_TO_COVER, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(100, 100, 100, 100))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(brk.get_cash() == 100)

    def testSellShortWithCommission(self):
        sharePrice = 100
        commission = 10
        brk = backtesting.Broker(1010, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE), commission=backtesting.FixedCommission(commission))

        # Sell 10 shares
        order = brk.create_market_order(broker.Order.Action.SELL_SHORT, BaseTestCase.TestInstrument, 10)
        brk.place_order(order)
        brk.on_bars(self.buildBars(sharePrice, sharePrice, sharePrice, sharePrice))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 10)
        self.assertTrue(brk.get_cash() == 2000)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -10)

        # Buy the 10 shares sold short plus 9 extra
        order = brk.create_market_order(broker.Order.Action.BUY_TO_COVER, BaseTestCase.TestInstrument, 19)
        brk.place_order(order)
        brk.on_bars(self.buildBars(sharePrice, sharePrice, sharePrice, sharePrice))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_commission() == 10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 9)
        self.assertTrue(brk.get_cash() == sharePrice - commission)

    def testCancel(self):
        brk = backtesting.Broker(100, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.cancel_order(order)
        brk.on_bars(self.buildBars(10, 10, 10, 10))
        self.assertTrue(order.is_canceled())

    def testReSubmit(self):
        brk = backtesting.Broker(1000, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1, False)
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())
        order.set_fill_on_close(True)
        self.assertTrue(order.is_dirty())
        brk.place_order(order) # Re-submit the order after changing it.
        self.assertTrue(not order.is_dirty())
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 12)

class LimitOrderTestCase(BaseTestCase):
    def testBuyAndSell_HitTarget_price(self):
        brk = backtesting.Broker(20, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 10, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(12, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Sell
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 15, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 17, 8, 10))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 15)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 25)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testBuyAndSell_GetBetterPrice(self):
        brk = backtesting.Broker(20, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 14, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(12, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 12)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 8)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Sell
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 15, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(16, 17, 8, 10))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 16)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 24)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testBuyAndSell_GappingBars(self):
        brk = backtesting.Broker(20, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Bar is below the target price.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 20, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 10))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Sell. Bar is above the target price.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 30, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(35, 40, 32, 35))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 35)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 45)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testFailToBuy(self):
        brk = backtesting.Broker(5, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        order = brk.create_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 5, 1)

        # Fail to buy (couldn't get specific price).
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_accepted())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 0)

        # Fail to buy (couldn't get specific price). Canceled due to session close.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.on_bars(self.buildBars(11, 15, 8, 12, True))
        self.assertTrue(order.is_canceled())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testBuy_GTC(self):
        brk = backtesting.Broker(10, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        order = brk.create_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 4, 2)
        order.set_good_until_canceled(True)

        # Fail to buy (couldn't get specific price).
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.place_order(order)
        # Set session_close to true test that the order doesn't get canceled.
        brk.on_bars(self.buildBars(10, 15, 8, 12, True))
        self.assertTrue(order.is_accepted())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 0)

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.on_bars(self.buildBars(2, 15, 1, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 2)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 6)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 2)
        self.assertTrue(cb.eventCount == 1)

    def testReSubmit(self):
        brk = backtesting.Broker(10, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        order = brk.create_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1, 1)
        order.set_good_until_canceled(True)

        # Fail to buy (couldn't get specific price).
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        order.set_limit_price(4)
        self.assertTrue(order.is_dirty())
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        order.set_quantity(2)
        self.assertTrue(order.is_dirty())
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        # Set session_close to true test that the order doesn't get canceled.
        brk.on_bars(self.buildBars(10, 15, 8, 12, True))
        self.assertTrue(order.is_accepted())
        self.assertTrue(order.get_execution_info() == None)
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 0)

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        brk.on_bars(self.buildBars(2, 15, 1, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 2)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 6)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 2)
        self.assertTrue(cb.eventCount == 1)

class StopOrderTestCase(BaseTestCase):
    def testLongPosStopLoss(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Create stop loss order.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 9, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 10, 12)) # Stop loss not hit.
        self.assertFalse(order.is_filled())
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 0)
        brk.on_bars(self.buildBars(10, 15, 8, 12)) # Stop loss hit.
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 9)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5+9)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testLongPosStopLoss_GappingBars(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Create stop loss order.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 9, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 10, 12)) # Stop loss not hit.
        self.assertFalse(order.is_filled())
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 0)
        brk.on_bars(self.buildBars(5, 8, 4, 7)) # Stop loss hit.
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 5)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5+5) # Fill the stop loss order at open price.
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testShortPosStopLoss(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Sell short
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.SELL_SHORT, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 15+10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(cb.eventCount == 1)

        # Create stop loss order.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_order(broker.Order.Action.BUY_TO_COVER, BaseTestCase.TestInstrument, 11, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(8, 10, 7, 9)) # Stop loss not hit.
        self.assertFalse(order.is_filled())
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 15+10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(cb.eventCount == 0)
        brk.on_bars(self.buildBars(10, 15, 8, 12)) # Stop loss hit.
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 11)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 15-1)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testShortPosStopLoss_GappingBars(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Sell short
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.SELL_SHORT, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 15+10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(cb.eventCount == 1)

        # Create stop loss order.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_order(broker.Order.Action.BUY_TO_COVER, BaseTestCase.TestInstrument, 11, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(8, 10, 7, 9)) # Stop loss not hit.
        self.assertFalse(order.is_filled())
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 15+10)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == -1)
        self.assertTrue(cb.eventCount == 0)
        brk.on_bars(self.buildBars(15, 20, 13, 14)) # Stop loss hit.
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 15)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 15-5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)

    def testReSubmit(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_market_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, 1)
        brk.place_order(order)
        brk.on_bars(self.buildBars(10, 15, 8, 12))
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)
        self.assertTrue(order.get_execution_info().get_commission() == 0)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 1)

        # Create stop loss order.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, 2, 1)
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        order.set_stop_price(9)
        self.assertTrue(order.is_dirty())
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        brk.on_bars(self.buildBars(10, 15, 10, 12)) # Stop loss not hit.
        self.assertFalse(order.is_filled())
        self.assertTrue(len(brk.get_pending_orders()) == 1)
        self.assertTrue(brk.get_cash() == 5)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 1)
        self.assertTrue(cb.eventCount == 0)
        brk.on_bars(self.buildBars(10, 15, 8, 12)) # Stop loss hit.
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 9)
        self.assertTrue(len(brk.get_pending_orders()) == 0)
        self.assertTrue(brk.get_cash() == 5+9)
        self.assertTrue(brk.get_shares(BaseTestCase.TestInstrument) == 0)
        self.assertTrue(cb.eventCount == 1)


class StopLimitOrderTestCase(BaseTestCase):
    def testFillOpen(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 10. Buy <= 12.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=10, limit_price=12, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(13, 15, 13, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit (bars include the price). Fill at open price.
        brk.on_bars(self.buildBars(11, 15, 10, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 11)

        # Sell. Stop <= 8. Sell >= 6.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=8, limit_price=6, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(9, 10, 9, 10))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(4, 5, 3, 4))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit (bars include the price). Fill at open price.
        brk.on_bars(self.buildBars(7, 8, 6, 7))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 7)

    def testFillOpen_GappingBars(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 10. Buy <= 12.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=10, limit_price=12, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(13, 18, 13, 17))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit (bars don't include the price). Fill at open price.
        brk.on_bars(self.buildBars(7, 9, 6, 8))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 7)

        # Sell. Stop <= 8. Sell >= 6.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=8, limit_price=6, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(9, 10, 9, 10))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(4, 5, 3, 4))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit (bars don't include the price). Fill at open price.
        brk.on_bars(self.buildBars(10, 12, 8, 10))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)

    def testFillLimit(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 10. Buy <= 12.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=10, limit_price=12, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(13, 15, 13, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at limit price.
        brk.on_bars(self.buildBars(13, 15, 10, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 12)

        # Sell. Stop <= 8. Sell >= 6.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=8, limit_price=6, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(9, 10, 9, 10))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(4, 5, 3, 4))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at limit price.
        brk.on_bars(self.buildBars(5, 7, 5, 6))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 6)

    def testHitStopAndLimit(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 10. Buy <= 12.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=10, limit_price=12, quantity=1)
        brk.place_order(order)

        # Stop price hit. Limit price hit. Fill at stop price.
        brk.on_bars(self.buildBars(9, 15, 8, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)

        # Sell. Stop <= 8. Sell >= 6.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=8, limit_price=6, quantity=1)
        brk.place_order(order)

        # Stop price hit. Limit price hit. Fill at stop price.
        brk.on_bars(self.buildBars(9, 10, 5, 8))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 8)

    def testInvertedPrices_FillOpen(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 12. Buy <= 10.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=12, limit_price=10, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(11, 12, 10.5, 11))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at open price.
        brk.on_bars(self.buildBars(9, 15, 8, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 9)

        # Sell. Stop <= 6. Sell >= 8.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=6, limit_price=8, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(9, 10, 9, 10))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(7, 7, 6, 7))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at open price.
        brk.on_bars(self.buildBars(9, 10, 8, 9))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 9)

    def testInvertedPrices_FillOpen_GappingBars(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 12. Buy <= 10.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=12, limit_price=10, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(11, 12, 10.5, 11))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at open price.
        brk.on_bars(self.buildBars(7, 9, 6, 8))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 7)

        # Sell. Stop <= 6. Sell >= 8.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=6, limit_price=8, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(9, 10, 9, 10))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(7, 7, 6, 7))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at open price.
        brk.on_bars(self.buildBars(10, 10, 9, 9))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)

    def testInvertedPrices_FillLimit(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 12. Buy <= 10.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=12, limit_price=10, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(11, 12, 10.5, 11))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at limit price.
        brk.on_bars(self.buildBars(11, 13, 8, 9))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)

        # Sell. Stop <= 6. Sell >= 8.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=6, limit_price=8, quantity=1)
        brk.place_order(order)

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(9, 10, 9, 10))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(7, 7, 6, 7))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit. Fill at limit price.
        brk.on_bars(self.buildBars(7, 10, 6, 9))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 8)

    def testInvertedPrices_HitStopAndLimit(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 12. Buy <= 10.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=12, limit_price=10, quantity=1)
        brk.place_order(order)

        # Stop price hit. Limit price hit. Fill at limit price.
        brk.on_bars(self.buildBars(9, 15, 8, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 10)

        # Sell. Stop <= 6. Sell >= 8.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.SELL, BaseTestCase.TestInstrument, stop_price=6, limit_price=8, quantity=1)
        brk.place_order(order)

        # Stop price hit. Limit price hit. Fill at limit price.
        brk.on_bars(self.buildBars(6, 10, 5, 7))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 8)

    def testReSubmit(self):
        brk = backtesting.Broker(15, bar_feed=barfeed.BarFeed(barfeed.Frequency.MINUTE))

        # Buy. Stop >= 10. Buy <= 12.
        cb = Callback()
        brk.get_order_updated_event().subscribe(cb.on_order_updated)
        order = brk.create_stop_limit_order(broker.Order.Action.BUY, BaseTestCase.TestInstrument, stop_price=1, limit_price=1, quantity=1)
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        order.set_limit_price(12)
        self.assertTrue(order.is_dirty())
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        order.set_stop_price(10)
        self.assertTrue(order.is_dirty())
        brk.place_order(order)
        self.assertTrue(not order.is_dirty())

        # Stop price not hit. Limit price not hit.
        brk.on_bars(self.buildBars(8, 9, 7, 8))
        self.assertFalse(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Stop price hit. Limit price not hit.
        brk.on_bars(self.buildBars(13, 15, 13, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_accepted())

        # Limit price hit (bars include the price). Fill at open price.
        brk.on_bars(self.buildBars(11, 15, 10, 14))
        self.assertTrue(order.is_limit_order_active())
        self.assertTrue(order.is_filled())
        self.assertTrue(order.get_execution_info().get_price() == 11)

def getTestCases():
    ret = []

    ret.append(BrokerTestCase("testRegressionGetActiveOrders"))

    ret.append(MarketOrderTestCase("testBuyAndSell"))
    ret.append(MarketOrderTestCase("testFailToBuy"))
    ret.append(MarketOrderTestCase("testBuy_GTC"))
    ret.append(MarketOrderTestCase("testBuyAndSellInTwoSteps"))
    ret.append(MarketOrderTestCase("testPortfolioValue"))
    ret.append(MarketOrderTestCase("testBuyWithCommission"))
    ret.append(MarketOrderTestCase("testSellShort_1"))
    ret.append(MarketOrderTestCase("testSellShort_2"))
    ret.append(MarketOrderTestCase("testSellShort_3"))
    ret.append(MarketOrderTestCase("testSellShortWithCommission"))
    ret.append(MarketOrderTestCase("testCancel"))
    ret.append(MarketOrderTestCase("testReSubmit"))

    ret.append(LimitOrderTestCase("testBuyAndSell_HitTarget_price"))
    ret.append(LimitOrderTestCase("testBuyAndSell_GetBetterPrice"))
    ret.append(LimitOrderTestCase("testBuyAndSell_GappingBars"))
    ret.append(LimitOrderTestCase("testFailToBuy"))
    ret.append(LimitOrderTestCase("testBuy_GTC"))
    ret.append(LimitOrderTestCase("testReSubmit"))

    ret.append(StopOrderTestCase("testLongPosStopLoss"))
    ret.append(StopOrderTestCase("testLongPosStopLoss_GappingBars"))
    ret.append(StopOrderTestCase("testShortPosStopLoss"))
    ret.append(StopOrderTestCase("testShortPosStopLoss_GappingBars"))
    ret.append(StopOrderTestCase("testReSubmit"))
    
    ret.append(StopLimitOrderTestCase("testFillOpen"))
    ret.append(StopLimitOrderTestCase("testFillOpen_GappingBars"))
    ret.append(StopLimitOrderTestCase("testFillLimit"))
    ret.append(StopLimitOrderTestCase("testHitStopAndLimit"))
    ret.append(StopLimitOrderTestCase("testInvertedPrices_FillOpen"))
    ret.append(StopLimitOrderTestCase("testInvertedPrices_FillOpen_GappingBars"))
    ret.append(StopLimitOrderTestCase("testInvertedPrices_FillLimit"))
    ret.append(StopLimitOrderTestCase("testInvertedPrices_HitStopAndLimit"))
    ret.append(StopLimitOrderTestCase("testReSubmit"))

    return ret

