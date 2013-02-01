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

from pytradelab import observer

######################################################################
## Orders
## http://stocks.about.com/od/tradingbasics/a/markords.htm
## http://www.interactivebrokers.com/en/software/tws/usersguidebook/ordertypes/basic_order_types.htm


class Order(object):
    """Base class for orders.

    :param type_: The order type
    :type type_: :class:`Order.Type`
    :param action: The order action.
    :type action: :class:`Order.Action`
    :param symbol: Instrument identifier.
    :type symbol: string.
    :param quantity: Order quantity.
    :type quantity: int.

    .. note::
        Valid **action** parameter values are:

        * Order.Action.BUY
        * Order.Action.BUY_TO_COVER
        * Order.Action.SELL
        * Order.Action.SELL_SHORT

        This is a base class and should not be used directly.
    """
    class Action:
        BUY	= 1
        BUY_TO_COVER = 2
        SELL = 3
        SELL_SHORT = 4

    class State:
        ACCEPTED = 1
        CANCELED = 2
        FILLED = 3

    class Type:
        MARKET = 1
        LIMIT = 2
        STOP = 3
        STOP_LIMIT = 4

    def __init__(self, type_, action, symbol, quantity):
        self.__type = type_
        self.__action = action
        self.__symbol = symbol
        self.__quantity = quantity
        self.__execution_info = None
        self.__good_until_canceled = False
        self.__all_or_none = True
        self.__state = Order.State.ACCEPTED
        self.__dirty = False

    def is_dirty(self):
        return self.__dirty

    def set_dirty(self, dirty):
        self.__dirty = dirty

    def get_type(self):
        """Returns the order type"""
        return self.__type

    def get_action(self):
        """Returns the order action."""
        return self.__action

    def get_state(self):
        """Returns the order state.

        Valid order states are:
        * Order.State.ACCEPTED (the initial state).
        * Order.State.CANCELED
        * Order.State.FILLED
        """
        return self.__state

    def is_accepted(self):
        """Returns True if the order state is Order.State.ACCEPTED."""
        return self.__state == Order.State.ACCEPTED

    def is_canceled(self):
        """Returns True if the order state is Order.State.CANCELED."""
        return self.__state == Order.State.CANCELED

    def is_filled(self):
        """Returns True if the order state is Order.State.FILLED."""
        return self.__state == Order.State.FILLED

    def get_symbol(self):
        """Returns the symbol identifier."""
        return self.__symbol

    def get_quantity(self):
        """Returns the quantity."""
        return self.__quantity

    def set_quantity(self, quantity):
        """Updates the quantity."""
        self.__quantity = quantity
        self.set_dirty(True)

    def get_good_until_canceled(self):
        """Returns True if the order is good till canceled."""
        return self.__good_until_canceled

    def set_good_until_canceled(self, good_until_canceled):
        """Sets if the order should be good till canceled.
        Orders that are not filled by the time the session closes will be will be automatically canceled
        if they were not set as good till canceled

        :param good_until_canceled: True if the order should be good till canceled.
        :type good_until_canceled: boolean.
        """
        self.__good_until_canceled = good_until_canceled
        self.set_dirty(True)

    def get_all_or_none(self):
        """Returns True if the order should be completely filled or else canceled."""
        return self.__all_or_none

    def set_all_or_none(self, all_or_none):
        """Sets the All-Or-None property for this order.

        :param all_or_none: True if the order should be completely filled or else canceled.
        :type all_or_none: boolean.
        """
        self.__all_or_none = all_or_none
        self.set_dirty(True)

    def set_execution_info(self, order_execution_info):
        self.__execution_info = order_execution_info
        self.__state = Order.State.FILLED

    def set_state(self, state):
        self.__state = state

    def get_execution_info(self):
        """Returns the order execution info if the order was filled, or None otherwise.

        :rtype: :class:`OrderExecutionInfo`.
        """
        return self.__execution_info


class MarketOrder(Order):
    """Base class for market orders.

    .. note::
        This is a base class and should not be used directly.
    """
    def __init__(self, action, symbol, quantity, on_close):
        Order.__init__(self, Order.Type.MARKET, action, symbol, quantity)
        self.__on_close = on_close

    def get_fill_on_close(self):
        """Returns True if the order should be filled as close to the closing price as possible (Market-On-Close order)."""
        return self.__on_close

    def set_fill_on_close(self, on_close):
        """Sets if the order should be filled as close to the closing price as possible (Market-On-Close order)."""
        self.__on_close = on_close
        self.set_dirty(True)


class LimitOrder(Order):
    """Base class for limit orders.

    .. note::
        This is a base class and should not be used directly.
    """
    def __init__(self, action, symbol, limit_price, quantity):
        Order.__init__(self, Order.Type.LIMIT, action, symbol, quantity)
        self.__limit_price = limit_price

    def get_limit_price(self):
        """Returns the limit price."""
        return self.__limit_price

    def set_limit_price(self, limit_price):
        """Updates the limit price."""
        self.__limit_price = limit_price
        self.set_dirty(True)


class StopOrder(Order):
    """Base class for stop orders.

    .. note::
        This is a base class and should not be used directly.
    """
    def __init__(self, action, symbol, stop_price, quantity):
        Order.__init__(self, Order.Type.STOP, action, symbol, quantity)
        self.__stop_price = stop_price

    def get_stop_price(self):
        """Returns the stop price."""
        return self.__stop_price

    def set_stop_price(self, stop_price):
        """Updates the stop price."""
        self.__stop_price = stop_price
        self.set_dirty(True)


class StopLimitOrder(Order):
    """Base class for stop limit orders.

    .. note::
        This is a base class and should not be used directly.
    """
    def __init__(self, action, symbol, limit_price, stop_price, quantity):
        Order.__init__(self, Order.Type.STOP_LIMIT, action, symbol, quantity)
        self.__limit_price = limit_price
        self.__stop_price = stop_price
        self.__limit_order_active = False # Set to true when the limit order is activated (stop price is hit)

    def get_limit_price(self):
        """Returns the limit price."""
        return self.__limit_price

    def set_limit_price(self, limit_price):
        """Updates the limit price."""
        self.__limit_price = limit_price
        self.set_dirty(True)

    def get_stop_price(self):
        """Returns the stop price."""
        return self.__stop_price

    def set_stop_price(self, stop_price):
        """Updates the stop price."""
        self.__stop_price = stop_price
        self.set_dirty(True)

    def set_limit_order_active(self, limit_order_active):
        self.__limit_order_active = limit_order_active

    def is_limit_order_active(self):
        """Returns True if the limit order is active."""
        return self.__limit_order_active


class OrderExecutionInfo(object):
    """Execution information for a filled order."""
    def __init__(self, price, quantity, commission, date_time):
        self.__price = price
        self.__quantity = quantity
        self.__commission = commission
        self.__date_time = date_time

    def get_price(self):
        """Returns the fill price."""
        return self.__price

    def get_quantity(self):
        """Returns the quantity."""
        return self.__quantity

    def get_commission(self):
        """Returns the commission applied."""
        return self.__commission

    def get_date_time(self):
        """Returns the :class:`datatime.datetime` when the order was executed."""
        return self.__date_time


######################################################################
## Base broker class
class Broker(object):
    """Base class for brokers.

    .. note::
        This is a base class and should not be used directly.
    """
    def __init__(self):
        self.__orderUpdatedEvent = observer.Event()

    def get_order_updated_event(self):
        return self.__orderUpdatedEvent

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def join(self):
        raise NotImplementedError()

    def get_shares(self, symbol):
        """Returns the number of shares for a symbol."""
        raise NotImplementedError()

    def get_positions(self):
        """Returns a dictionary that maps symbols to shares."""
        raise NotImplementedError()

    def get_active_orders(self):
        """Returns a sequence with the orders that are still active."""
        raise NotImplementedError()

    # Return True if there are not more events to dispatch.
    def stop_dispatching(self):
        raise NotImplementedError()

    # Dispatch events.
    def dispatch(self):
        raise NotImplementedError()

    def place_order(self, order):
        """Submits an order.

        :param order: The order to submit.
        :type order: :class:`Order`.

        .. note::
            If the order is filled or canceled, an exception will be raised.
        """
        raise NotImplementedError()

    def create_market_order(self, action, symbol, quantity, on_close=False):
        """Creates a Market order.
        A market order is an order to buy or sell a stock at the best available price.
        Generally, this type of order will be executed immediately. However, the price at which a market order will be executed
        is not guaranteed.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param symbol: Instrument identifier.
        :type symbol: string.
        :param quantity: Order quantity.
        :type quantity: int.
        :param on_close: True if the order should be filled as close to the closing price as possible (Market-On-Close order). Default is False.
        :type on_close: boolean.
        :rtype: A :class:`MarketOrder` subclass.
        """
        raise NotImplementedError()

    def create_limit_order(self, action, symbol, limit_price, quantity):
        """Creates a Limit order.
        A limit order is an order to buy or sell a stock at a specific price or better.
        A buy limit order can only be executed at the limit price or lower, and a sell limit order can only be executed at the
        limit price or higher.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param symbol: Instrument identifier.
        :type symbol: string.
        :param limit_price: The order price.
        :type limit_price: float
        :param quantity: Order quantity.
        :type quantity: int.
        :rtype: A :class:`LimitOrder` subclass.
        """
        raise NotImplementedError()

    def create_stop_order(self, action, symbol, stop_price, quantity):
        """Creates a Stop order.
        A stop order, also referred to as a stop-loss order, is an order to buy or sell a stock once the price of the stock
        reaches a specified price, known as the stop price.
        When the stop price is reached, a stop order becomes a market order.
        A buy stop order is entered at a stop price above the current market price. Investors generally use a buy stop order
        to limit a loss or to protect a profit on a stock that they have sold short.
        A sell stop order is entered at a stop price below the current market price. Investors generally use a sell stop order
        to limit a loss or to protect a profit on a stock that they own.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param symbol: Instrument identifier.
        :type symbol: string.
        :param stop_price: The trigger price.
        :type stop_price: float
        :param quantity: Order quantity.
        :type quantity: int.
        :rtype: A :class:`StopOrder` subclass.
        """
        raise NotImplementedError()

    def create_stop_limit_order(self, action, symbol, stop_price, limit_price, quantity):
        """Creates a Stop-Limit order.
        A stop-limit order is an order to buy or sell a stock that combines the features of a stop order and a limit order.
        Once the stop price is reached, a stop-limit order becomes a limit order that will be executed at a specified price
        (or better). The benefit of a stop-limit order is that the investor can control the price at which the order can be executed.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param symbol: Instrument identifier.
        :type symbol: string.
        :param stop_price: The trigger price.
        :type stop_price: float
        :param limit_price: The price for the limit order.
        :type limit_price: float
        :param quantity: Order quantity.
        :type quantity: int.
        :rtype: A :class:`StopLimitOrder` subclass.
        """
        raise NotImplementedError()

    def cancel_order(self, order):
        """Requests an order to be canceled. If the order is filled an Exception is raised.

        :param order: The order to cancel.
        :type order: :class:`Order`.
        """
        raise NotImplementedError()
