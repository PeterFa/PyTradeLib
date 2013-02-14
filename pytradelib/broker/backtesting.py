# This file was originally part of PyAlgoTrade.
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

from pytradelib import broker
from pytradelib import warninghelpers
import pytradelib.logger
import copy

logger = pytradelib.logger.get_logger("broker.backtesting")


######################################################################
## Commissions

class Commission(object):
    def calculate(self, order, price, quantity):
        raise NotImplementedError()

class NoCommission(Commission):
    def calculate(self, order, price, quantity):
        return 0

class FixedCommission(Commission):
    def __init__(self, cost):
        self.__cost = cost

    def calculate(self, order, price, quantity):
        return self.__cost


######################################################################
## Order filling strategies

class FillStrategy(object):
    """Base class for order filling strategies."""

    # Return the fill price for a MarketOrder or None.
    def fill_market_order(self, order, broker_, bar):
        """Override to return the fill price for a market order or None if the order can't be filled at the given time.

        :param order: The order.
        :type order: :class:`pytradelib.broker.MarketOrder`.
        :param broker_: The broker.
        :type broker_: :class:`Broker`.
        :param bar: The current bar.
        :type bar: :class:`pytradelib.bar.Bar`.
        :rtype: An int/float with the fill price or None if the order should not be filled.
        """
        raise NotImplementedError()

    # Return the fill price for a LimitOrder or None.
    def fill_limit_order(self, order, broker_, bar):
        """Override to return the fill price for a limit order or None if the order can't be filled at the given time.

        :param order: The order.
        :type order: :class:`pytradelib.broker.LimitOrder`.
        :param broker_: The broker.
        :type broker_: :class:`Broker`.
        :param bar: The current bar.
        :type bar: :class:`pytradelib.bar.Bar`.
        :rtype: An int/float with the fill price or None if the order should not be filled.
        """
        raise NotImplementedError()

    # Return the fill price for a StopOrder or None.
    def fill_stop_order(self, order, broker_, bar):
        """Override to return the fill price for a stop order or None if the order can't be filled at the given time.

        :param order: The order.
        :type order: :class:`pytradelib.broker.StopOrder`.
        :param broker_: The broker.
        :type broker_: :class:`Broker`.
        :param bar: The current bar.
        :type bar: :class:`pytradelib.bar.Bar`.
        :rtype: An int/float with the fill price or None if the order should not be filled.
        """
        raise NotImplementedError()

    # Return the fill price for a StopLimitOrder or None.
    def fill_stop_limit_order(self, order, broker_, bar, just_hit_stop_price):
        """Override to return the fill price for a stop limit order or None if the order can't be filled at the given time.

        :param order: The order.
        :type order: :class:`pytradelib.broker.StopLimitOrder`.
        :param broker_: The broker.
        :type broker_: :class:`Broker`.
        :param bar: The current bar.
        :type bar: :class:`pytradelib.bar.Bar`.
        :param just_hit_stop_price: True if the stop price has just been hit with the current bar.
        :type just_hit_stop_price: boolean.
        :rtype: An int/float with the fill price or None if the order should not be filled.
        """
        raise NotImplementedError()

class DefaultStrategy(FillStrategy):
    """
    This strategy works as follows:

    * A :class:`pytradelib.broker.MarketOrder` is always filled using the open/close price.
    * A :class:`pytradelib.broker.LimitOrder` will be filled like this:
        * If the limit price was penetrated with the open price, then the open price is used.
        * If the bar includes the limit price, then the limit price is used.
        * Note that when buying the price is penetrated if it gets <= the limit price, and when selling the price is penetrated if it gets >= the limit price
    * A :class:`pytradelib.broker.StopOrder` will be filled like this:
        * If the stop price was penetrated with the open price, then the open price is used.
        * If the bar includes the stop price, then the stop price is used.
        * Note that when buying the price is penetrated if it gets >= the stop price, and when selling the price is penetrated if it gets <= the stop price
    * A :class:`pytradelib.broker.StopLimitOrder` will be filled like this:
        * If the stop price was penetrated with the open price, or if the bar includes the stop price, then the limit order becomes active.
        * If the limit order is active:
            * If the limit order was activated in this same bar and the limit price is penetrated as well, then the best between the stop price and the limit fill price (as described earlier) is used.
            * If the limit order was activated at a previous bar then the limit fill price (as described earlier) is used.

    .. note::
        This is the default strategy used by the Broker.
    """
    def __get_limit_order_fill_price(self, broker_, bar_, action, limit_price):
        ret = None
        open_ = broker_.get_bar_open(bar_)
        high = broker_.get_bar_high(bar_)
        low = broker_.get_bar_low(bar_)

        # If the bar is below the limit price, use the open price.
        # If the bar includes the limit price, use the open price or the limit price.
        if action in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
            if high < limit_price:
                ret = open_
            elif limit_price >= low:
                if open_ < limit_price: # The limit price was penetrated on open.
                    ret = open_
                else:
                    ret = limit_price
        # If the bar is above the limit price, use the open price.
        # If the bar includes the limit price, use the open price or the limit price.
        elif action in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
            if low > limit_price:
                ret = open_
            elif limit_price <= high:
                if open_ > limit_price: # The limit price was penetrated on open.
                    ret = open_
                else:
                    ret = limit_price
        else: # Unknown action
            assert(False)
        return ret

    def fill_market_order(self, order, broker_, bar):
        if order.get_fill_on_close():
            ret = broker_.get_bar_close(bar)
        else:
            ret = broker_.get_bar_open(bar)
        return ret

    # Return the fill price for a LimitOrder or None.
    def fill_limit_order(self, order, broker_, bar):
        return self.__get_limit_order_fill_price(broker_, bar, order.get_action(), order.get_limit_price())

    # Return the fill price for a StopOrder or None.
    def fill_stop_order(self, order, broker_, bar):
        ret = None
        open_ = broker_.get_bar_open(bar)
        high = broker_.get_bar_high(bar)
        low = broker_.get_bar_low(bar)
        stop_price = order.get_stop_price()

        # If the bar is above the stop price, use the open price.
        # If the bar includes the stop price, use the open price or the stop price. Whichever is better.
        if order.get_action() in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
            if low > stop_price:
                ret = open_
            elif stop_price <= high:
                if open_ > stop_price: # The stop price was penetrated on open.
                    ret = open_
                else:
                    ret = stop_price
        # If the bar is below the stop price, use the open price.
        # If the bar includes the stop price, use the open price or the stop price. Whichever is better.
        elif order.get_action() in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
            if high < stop_price:
                ret = open_
            elif stop_price >= low:
                if open_ < stop_price: # The stop price was penetrated on open.
                    ret = open_
                else:
                    ret = stop_price
        else: # Unknown action
            assert(False)
        return ret

    # Return the fill price for a StopLimitOrder or None.
    def fill_stop_limit_order(self, order, broker_, bar, just_hit_stop_price):
        ret = self.__get_limit_order_fill_price(broker_, bar, order.get_action(), order.get_limit_price())
        # If we just hit the stop price, we need to make additional checks.
        if ret != None and just_hit_stop_price:
            if order.get_action() in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
                # If the stop price is lower than the limit price, then use that one. Else use the limit price.
                ret = min(order.get_stop_price(), order.get_limit_price())
            elif order.get_action() in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
                # If the stop price is greater than the limit price, then use that one. Else use the limit price.
                ret = max(order.get_stop_price(), order.get_limit_price())
            else: # Unknown action
                assert(False)
        return ret


######################################################################
## Orders

class BacktestingOrder(object):
    def __init__(self):
        pass

    def check_canceled(self, broker, bars):
        # This check is only for accepted orders that are not GTC.
        if self.get_good_until_canceled() or not self.is_accepted():
            return

        # If its the last bar of the session and the order was not filled then cancel it.
        bar_ = bars.get_bar(self.get_symbol())
        if bar_ != None and bar_.get_session_close():
            broker.cancel_order(self)

    def try_execute(self, broker, bars):
        if self.is_accepted():
            # Process the order if there is data available.
            bar_ = bars.get_bar(self.get_symbol())
            if bar_ != None:
                self.try_execute_implementation(broker, bar_)
            # Check if the order has to be canceled.
            self.check_canceled(broker, bars)

class MarketOrder(broker.MarketOrder, BacktestingOrder):
    def __init__(self, action, symbol, quantity, on_close):
        broker.MarketOrder.__init__(self, action, symbol, quantity, on_close)
        BacktestingOrder.__init__(self)

    def try_execute_implementation(self, broker_, bar_):
        price = broker_.get_fill_strategy().fill_market_order(self, broker_, bar_)
        if price != None:
            broker_.commit_order_execution(self, price, self.get_quantity(), bar_.get_date_time())

class LimitOrder(broker.LimitOrder, BacktestingOrder):
    def __init__(self, action, symbol, limit_price, quantity):
        broker.LimitOrder.__init__(self, action, symbol, limit_price, quantity)
        BacktestingOrder.__init__(self)

    def try_execute_implementation(self, broker_, bar_):
        price = broker_.get_fill_strategy().fill_limit_order(self, broker_, bar_)
        if price != None:
            broker_.commit_order_execution(self, price, self.get_quantity(), bar_.get_date_time())

class StopOrder(broker.StopOrder, BacktestingOrder):
    def __init__(self, action, symbol, stop_price, quantity):
        broker.StopOrder.__init__(self, action, symbol, stop_price, quantity)
        BacktestingOrder.__init__(self)

    def try_execute_implementation(self, broker_, bar_):
        price = broker_.get_fill_strategy().fill_stop_order(self, broker_, bar_)
        if price != None:
            broker_.commit_order_execution(self, price, self.get_quantity(), bar_.get_date_time())

# http://www.sec.gov/answers/stoplim.htm
# http://www.interactivebrokers.com/en/trading/orders/stopLimit.php
class StopLimitOrder(broker.StopLimitOrder, BacktestingOrder):
    def __init__(self, action, symbol, limit_price, stop_price, quantity):
        broker.StopLimitOrder.__init__(self, action, symbol, limit_price, stop_price, quantity)
        BacktestingOrder.__init__(self)

    def __stop_hit(self, broker_, bar_):
        ret = False
        high = broker_.get_bar_high(bar_)
        low = broker_.get_bar_low(bar_)
        stop_price = self.get_stop_price()

        # If the bar is above the stop price, or the bar includes the stop price, the stop was hit.
        if self.get_action() in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
            if low >= stop_price or stop_price <= high:
                ret = True
        # If the bar is below the stop price, or the bar includes the stop price, the stop was hit.
        elif self.get_action() in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
            if high <= stop_price or stop_price >= low:
                ret = True
        else: # Unknown action
            assert(False)
        return ret

    def try_execute_implementation(self, broker_, bar_):
        just_hit_stop_price = False

        # Check if we have to activate the limit order first.
        if not self.is_limit_order_active() and self.__stop_hit(broker_, bar_):
            self.set_limit_order_active(True)
            just_hit_stop_price = True

        # Check if we have ever reached the limit price
        if self.is_limit_order_active():
            price = broker_.get_fill_strategy().fill_stop_limit_order(self, broker_, bar_, just_hit_stop_price)
            if price != None:
                broker_.commit_order_execution(self, price, self.get_quantity(), bar_.get_date_time())


######################################################################
## Broker

class Broker(broker.Broker):
    """Backtesting broker.

    :param cash: The initial amount of cash.
    :type cash: int or float.
    :param bar_feed: The bar feed that will provide the bars.
    :type bar_feed: :class:`pytradelib.barfeed.BarFeed`
    :param commission: An object responsible for calculating order commissions.
    :type commission: :class:`Commission`
    """

    def __init__(self, cash, bar_feed, commission=None):
        broker.Broker.__init__(self)

        assert(cash >= 0)
        self.__cash = cash
        if commission is None:
            self.__commission = NoCommission()
        else:
            self.__commission = commission
        self.__shares = {}
        self.__active_orders = []
        self.__use_adj_values = False
        self.__fill_strategy = DefaultStrategy()

        # It is VERY important that the broker subscribes to barfeed events before the strategy.
        bar_feed.get_new_bars_event().subscribe(self.on_bars)
        self.__bar_feed = bar_feed
        self.__allow_negative_cash = False

    def __get_bar(self, bars, symbol):
        ret = bars.get_bar(symbol)
        if ret == None:
            ret = self.__bar_feed.get_last_bar(symbol)
        return ret

    def set_allow_negative_cash(self, allow_negative_cash):
        self.__allow_negative_cash = allow_negative_cash

    def get_cash(self):
        """Returns the available cash."""
        return self.__cash

    def set_cash(self, cash):
        """Sets the available cash."""
        self.__cash = cash

    def get_commission(self):
        """Returns the commission instance."""
        return self.__commission

    def set_commission(self, commission):
        """Sets the commission instance."""
        self.__commission = commission

    def set_fill_strategy(self, strategy):
        """Sets the :class:`FillStrategy` to use."""
        self.__fill_strategy = strategy

    def get_fill_strategy(self):
        """Returns the :class:`FillStrategy` currently set."""
        return self.__fill_strategy

    def get_bar_open(self, bar_):
        if self.get_use_adj_values():
            ret = bar_.get_adj_open()
        else:
            ret = bar_.get_open()
        return ret

    def get_bar_high(self, bar_):
        if self.get_use_adj_values():
            ret = bar_.get_adj_high()
        else:
            ret = bar_.get_high()
        return ret

    def get_bar_low(self, bar_):
        if self.get_use_adj_values():
            ret = bar_.get_adj_low()
        else:
            ret = bar_.get_low()
        return ret

    def get_bar_close(self, bar_):
        if self.get_use_adj_values():
            ret = bar_.get_adj_close()
        else:
            ret = bar_.get_close()
        return ret

    def get_use_adj_values(self):
        return self.__use_adj_values

    def set_use_adj_values(self, use_adjusted):
        self.__use_adj_values = use_adjusted

    def get_active_orders(self):
        return self.__active_orders

    def get_pending_orders(self):
        warninghelpers.deprecation_warning("get_pending_orders will be deprecated in the next version. Please use get_active_orders instead.", stacklevel=2)
        return self.get_active_orders()

    def get_shares(self, symbol):
        self.__shares.setdefault(symbol, 0)
        return self.__shares[symbol]

    def get_positions(self):
        return self.__shares

    def get_active_symbols(self):
        return [symbol for symbol, shares in self.__shares.iteritems() if shares != 0]

    def get_equity_with_bars(self, bars):
        ret = self.get_cash()
        if bars != None:
            for symbol, shares in self.__shares.iteritems():
                symbol_price = self.get_bar_close(self.__get_bar(bars, symbol))
                ret += symbol_price * shares
        return ret

    def get_value(self, deprecated = None):
        if deprecated != None:
            warninghelpers.deprecation_warning("The bars parameter is no longer used and will be removed in the next version.", stacklevel=2)

        return self.get_equity_with_bars(self.__bar_feed.get_current_bars())

    def get_equity(self):
        """Returns the portfolio value (cash + shares)."""
        return self.get_equity_with_bars(self.__bar_feed.get_current_bars())

    # Tries to commit an order execution. Returns True if the order was commited, or False is there is not enough cash.
    def commit_order_execution(self, order, price, quantity, date_time):
        if order.get_action() in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
            cost = price * quantity * -1
            assert(cost < 0)
            shares_delta = quantity
        elif order.get_action() in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
            cost = price * quantity
            assert(cost > 0)
            shares_delta = quantity * -1
        else: # Unknown action
            assert(False)

        ret = False
        commission = self.get_commission().calculate(order, price, quantity)
        cost -= commission
        resulting_cash = self.get_cash() + cost

        # Check that we're ok on cash after the commission.
        if resulting_cash >= 0 or self.__allow_negative_cash:
            # Commit the order execution.
            self.set_cash(resulting_cash)
            self.__shares[order.get_symbol()] = self.get_shares(order.get_symbol()) + shares_delta
            ret = True

            # Update the order.
            order_execution_info = broker.OrderExecutionInfo(price, quantity, commission, date_time)
            order.set_execution_info(order_execution_info)
        else:
            logger.debug("Not enough money to fill order %s" % (order))
        return ret

    def place_order(self, order):
        if order.is_accepted():
            if order not in self.__active_orders:
                self.__active_orders.append(order)
            order.set_dirty(False)
        else:
            raise Exception("The order was already processed")

    def on_bars(self, bars):
        active_orders = copy.copy(self.__active_orders)

        for order in active_orders:
            if order.is_accepted():
                order.try_execute(self, bars)
                if not order.is_accepted():
                    self.__active_orders.remove(order)
                    self.get_order_updated_event().emit(self, order)
            else:
                self.__active_orders.remove(order)
                self.get_order_updated_event().emit(self, order)

    def start(self):
        pass

    def stop(self):
        pass

    def join(self):
        pass

    def stop_dispatching(self):
        # If there are no more events in the barfeed, then there is nothing left for us to do since all processing took
        # place while processing barfeed events.
        return self.__bar_feed.stop_dispatching()

    def dispatch(self):
        # All events were already emitted while handling barfeed events.
        pass

    def create_market_order(self, action, symbol, quantity, on_close=False):
        return MarketOrder(action, symbol, quantity, on_close)

    def create_limit_order(self, action, symbol, limit_price, quantity):
        return LimitOrder(action, symbol, limit_price, quantity)

    def create_stop_order(self, action, symbol, stop_price, quantity):
        return StopOrder(action, symbol, stop_price, quantity)

    def create_stop_limit_order(self, action, symbol, stop_price, limit_price, quantity):
        return StopLimitOrder(action, symbol, limit_price, stop_price, quantity)

    def cancel_order(self, order):
        if order.is_filled():
            raise Exception("Can't cancel order that has already been filled")
        order.set_state(broker.Order.State.CANCELED)
