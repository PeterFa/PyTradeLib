# PyAlgoTrade
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

import broker
import broker.backtesting
import observer
from stratanalyzer import returns
import warninghelpers

class Position:
    """Base class for positions.

    :param strategy: The strategy that this position belongs to.
    :type strategy: :class:`pyalgotrade.strategy.Strategy`.
    :param entry_order: The order used to enter the position.
    :type entry_order: :class:`pyalgotrade.broker.Order`
    :param good_until_canceled: True if the entry order should be set as good until canceled.
    :type good_until_canceled: boolean.

    .. note::
        This is a base class and should not be used directly.
    """

    def __init__(self, strategy, entry_order, good_until_canceled):
        self.__strategy = strategy
        self.__entry_order = entry_order
        self.__exit_order = None
        self.__exit_on_session_close = False
        entry_order.set_good_until_canceled(good_until_canceled)
        self.__exit_date_time = None

    def get_strategy(self):
        return self.__strategy

    def entry_filled(self):
        """ Returns True if the entry order was filled."""
        return self.__entry_order != None and self.__entry_order.is_filled()

    def exit_filled(self):
        """ Returns True if the exit order was filled."""
        return self.__exit_order != None and self.__exit_order.is_filled()

    def get_good_until_canceled(self):
        return self.__entry_order.get_good_until_canceled()

    def set_exit_on_session_close(self, exit_on_session_close):
        """ Set to True to automatically place an exit order when the session is
        about to close. Only useful for intraday trading.

        .. note::
            If the entry order was not filled by the time the session is about
            to close, it will get canceled.
        """
        self.__exit_on_session_close = exit_on_session_close

    def get_exit_on_session_close(self):
        """ Returns True if an order to exit the position should be
        automatically submitted when the session is about to close."""
        return self.__exit_on_session_close

    def get_entry_order(self):
        """ Returns the :class:`pyalgotrade.broker.Order` used to enter the
        position."""
        return self.__entry_order

    def set_exit_order(self, exit_order):
        self.__exit_order = exit_order

    def get_exit_order(self):
        """Returns the :class:`pyalgotrade.broker.Order` used to exit the
        position. If this position hasn't been closed yet, None is returned."""
        return self.__exit_order

    def get_symbol(self):
        """Returns the symbol used for this position."""
        return self.__entry_order.get_symbol()

    def get_quantity(self):
        """Returns the number of shares used to enter this position."""
        return self.__entry_order.get_quantity()

    def close(self, limit_price, stop_price, good_until_canceled=None):
        # If a previous exit order was pending, cancel it.
        if self.get_exit_order() != None:
            self.get_strategy().get_broker().cancel_order(self.get_exit_order())

        close_order = self.build_exit_order(limit_price, stop_price)

        # If good_until_canceled was not set, match the entry order.
        if good_until_canceled == None:
            good_until_canceled = self.__entry_order.get_good_until_canceled()
        close_order.set_good_until_canceled(good_until_canceled)

        self.get_strategy().get_broker().place_order(close_order)
        self.set_exit_order(close_order)

    def check_exit_on_session_close(self, bars):
        ret = None
        # If the position was set to exit on session close and this is the
        # penultimate bar then:
        # * Create the exit order if the entry was filled.
        # * Cancel the entry order if it was not filled so far.
        if self.__exit_on_session_close and self.__exit_order == None:
            bar = bars.get_bar(self.get_symbol())
            if bar and bar.get_bars_until_session_close() == 1:
                if self.entry_filled():
                    ret = self.build_exit_on_session_close_order()
                    self.get_strategy().get_broker().place_order(ret)
                    self.set_exit_order(ret)
                else:
                    self.get_strategy().get_broker().cancel_order(self.get_entry_order())
        return ret

    def get_return(self, include_commissions=True):
        """Returns the position's returns."""
        if not self.entry_filled():
            raise Exception("Position not opened yet")
        elif not self.exit_filled():
            raise Exception("Position not closed yet")
        return self.get_return_implementation(include_commissions)

    def get_result(self):
        """Returns the ratio between the order prices. It **doesn't** include commisions."""
        warninghelpers.deprecation_warning("get_result will be deprecated in the next version. Please use get_return instead.", stacklevel=2)
        return self.get_return(False)

    def get_return_implementation(self, include_commissions):
        raise NotImplementedError()

    def get_net_profit(self, include_commissions=True):
        """Returns the position's net profit."""
        if not self.entry_filled():
            raise Exception("Position not opened yet")
        elif not self.exit_filled():
            raise Exception("Position not closed yet")
        return self.get_net_profit_implementation(include_commissions)

    def get_net_profit_implementation(self, include_commissions):
        raise NotImplementedError()

    def build_exit_order(self, limit_price, stop_price):
        raise NotImplementedError()

    def build_exit_on_session_close_order(self):
        raise NotImplementedError()

    def is_long(self):
        raise NotImplementedError()

    def is_short(self):
        return not self.is_long()

# This class is reponsible for order management in long positions.
class LongPosition(Position):
    def __init__(self, strategy, symbol, limit_price, stop_price, quantity, good_until_canceled):
        if limit_price == None and stop_price == None:
            entry_order = strategy.get_broker().create_market_order(broker.Order.Action.BUY, symbol, quantity, False)
        elif limit_price != None and stop_price == None:
            entry_order = strategy.get_broker().create_limit_order(broker.Order.Action.BUY, symbol, limit_price, quantity)
        elif limit_price == None and stop_price != None:
            entry_order = strategy.get_broker().create_stop_order(broker.Order.Action.BUY, symbol, stop_price, quantity)
        elif limit_price != None and stop_price != None:
            entry_order = strategy.get_broker().create_stop_limit_order(broker.Order.Action.BUY, symbol, stop_price, limit_price, quantity)
        else:
            assert(False)

        Position.__init__(self, strategy, entry_order, good_until_canceled)
        strategy.get_broker().place_order(entry_order)

    def __get_position_tracker(self):
        ret = returns.PositionTracker()
        entry_exec_info = self.get_entry_order().get_execution_info()
        exit_exec_info = self.get_exit_order().get_execution_info()
        ret.buy(entry_exec_info.get_quantity(), entry_exec_info.get_price(), entry_exec_info.get_commission())
        ret.sell(exit_exec_info.get_quantity(), exit_exec_info.get_price(), exit_exec_info.get_commission())
        return ret

    def get_return_implementation(self, include_commissions):
        return self.__get_position_tracker().get_return(self.get_exit_order().get_execution_info().get_price(), include_commissions)

    def get_net_profit_implementation(self, include_commissions):
        return self.__get_position_tracker().get_net_profit(self.get_exit_order().get_execution_info().get_price(), include_commissions)

    def build_exit_order(self, limit_price, stop_price):
        if limit_price == None and stop_price == None:
            ret = self.get_strategy().get_broker().create_market_order(broker.Order.Action.SELL, self.get_symbol(), self.get_quantity(), False)
        elif limit_price != None and stop_price == None:
            ret = self.get_strategy().get_broker().create_limit_order(broker.Order.Action.SELL, self.get_symbol(), limit_price, self.get_quantity())
        elif limit_price == None and stop_price != None:
            ret = self.get_strategy().get_broker().create_stop_order(broker.Order.Action.SELL, self.get_symbol(), stop_price, self.get_quantity())
        elif limit_price != None and stop_price != None:
            ret = self.get_strategy().get_broker().create_stop_limit_order(broker.Order.Action.SELL, self.get_symbol(), stop_price, limit_price, self.get_quantity())
        else:
            assert(False)

        return ret

    def build_exit_on_session_close_order(self):
        ret = self.get_strategy().get_broker().create_market_order(broker.Order.Action.SELL, self.get_symbol(), self.get_quantity(), True)
        ret.set_good_until_canceled(True) # Mark the exit order as GTC since we want to exit ASAP and avoid this order to get canceled.
        return ret

    def is_long(self):
        return True

# This class is reponsible for order management in short positions.
class ShortPosition(Position):
    def __init__(self, strategy, symbol, limit_price, stop_price, quantity, good_until_canceled):
        if limit_price == None and stop_price == None:
            entry_order = strategy.get_broker().create_market_order(broker.Order.Action.SELL_SHORT, symbol, quantity, False)
        elif limit_price != None and stop_price == None:
            entry_order = strategy.get_broker().create_limit_order(broker.Order.Action.SELL_SHORT, symbol, limit_price, quantity)
        elif limit_price == None and stop_price != None:
            entry_order = strategy.get_broker().create_stop_order(broker.Order.Action.SELL_SHORT, symbol, stop_price, quantity)
        elif limit_price != None and stop_price != None:
            entry_order = strategy.get_broker().create_stop_limit_order(broker.Order.Action.SELL_SHORT, symbol, stop_price, limit_price, quantity)
        else:
            assert(False)

        Position.__init__(self, strategy, entry_order, good_until_canceled)
        strategy.get_broker().place_order(entry_order)

    def __get_position_tracker(self):
        ret = returns.PositionTracker()
        entry_exec_info = self.get_entry_order().get_execution_info()
        exit_exec_info = self.get_exit_order().get_execution_info()
        ret.sell(entry_exec_info.get_quantity(), entry_exec_info.get_price(), entry_exec_info.get_commission())
        ret.buy(exit_exec_info.get_quantity(), exit_exec_info.get_price(), exit_exec_info.get_commission())
        return ret

    def get_return_implementation(self, include_commissions):
        return self.__get_position_tracker().get_return(self.get_exit_order().get_execution_info().get_price(), include_commissions)

    def get_net_profit_implementation(self, include_commissions):
        return self.__get_position_tracker().get_net_profit(self.get_exit_order().get_execution_info().get_price(), include_commissions)

    def build_exit_order(self, limit_price, stop_price):
        if limit_price == None and stop_price == None:
            ret = self.get_strategy().get_broker().create_market_order(broker.Order.Action.BUY_TO_COVER, self.get_symbol(), self.get_quantity(), False)
        elif limit_price != None and stop_price == None:
            ret = self.get_strategy().get_broker().create_limit_order(broker.Order.Action.BUY_TO_COVER, self.get_symbol(), limit_price, self.get_quantity())
        elif limit_price == None and stop_price != None:
            ret = self.get_strategy().get_broker().create_stop_order(broker.Order.Action.BUY_TO_COVER, self.get_symbol(), stop_price, self.get_quantity())
        elif limit_price != None and stop_price != None:
            ret = self.get_strategy().get_broker().create_stop_limit_order(broker.Order.Action.BUY_TO_COVER, self.get_symbol(), stop_price, limit_price, self.get_quantity())
        else:
            assert(False)

        return ret

    def build_exit_on_session_close_order(self):
        ret = self.get_strategy().get_broker().create_market_order(broker.Order.Action.BUY_TO_COVER, self.get_symbol(), self.get_quantity(), True)
        ret.set_good_until_canceled(True) # Mark the exit order as GTC since we want to exit ASAP and avoid this order to get canceled.
        return ret

    def is_long(self):
        return False

class Strategy:
    """Base class for strategies.

    :param bar_feed: The bar feed to use to backtest the strategy.
    :type bar_feed: :class:`pyalgotrade.barfeed.BarFeed`.
    :param cash: The amount of cash available.
    :type cash: int/float.
    :param broker_: Broker to use. If not specified the default backtesting broker (:class:`pyalgotrade.broker.backtesting.Broker`)
                    will be used.
    :type broker_: :class:`pyalgotrade.broker.Broker`.

    .. note::
        This is a base class and should not be used directly.
    """

    def __init__(self, bar_feed, cash=25000, broker_=None):
        self.__feed = bar_feed
        self.__active_positions = {}
        self.__order_to_position = {}
        self.__bars_processed_event = observer.Event()
        self.__analyzers = []
        self.__named_analyzers = {}

        if broker_ == None:
            # When doing backtesting (broker_ == None), the broker should subscribe to bar_feed events before the strategy.
            # This is to avoid executing orders placed in the current tick.
            self.__broker = broker.backtesting.Broker(cash, bar_feed)
        else:
            self.__broker = broker_
        self.__broker.get_order_updated_event().subscribe(self.__on_order_update)

    def get_result(self):
        return self.get_broker().get_equity()

    def get_bars_processed_event(self):
        return self.__bars_processed_event

    def __register_order(self, position, order):
        try:
            orders = self.__active_positions[position]
        except KeyError:
            orders = set()
            self.__active_positions[position] = orders

        if order.is_accepted():
            self.__order_to_position[order] = position
            orders.add(order)

    def __unregister_order(self, position, order):
        del self.__order_to_position[order]

        orders = self.__active_positions[position]
        orders.remove(order)
        if len(orders) == 0:
            del self.__active_positions[position]

    def __register_active_position(self, position):
        for order in [position.get_entry_order(), position.get_exit_order()]:
            if order and order.is_accepted():
                self.__register_order(position, order)

    def __notify_analyzers(self, lambda_expression):
        for s in self.__analyzers:
            lambda_expression(s)

    def attach_analyzer_ex(self, strategy_analyzer, name=None):
        if strategy_analyzer not in self.__analyzers:
            if name != None:
                if name in self.__named_analyzers:
                    raise Exception("A different analyzer named '%s' was already attached" % name)
                self.__named_analyzers[name] = strategy_analyzer

            strategy_analyzer.before_attach(self)
            self.__analyzers.append(strategy_analyzer)
            strategy_analyzer.attached(self)

    def attach_analyzer(self, strategy_analyzer):
        """Adds a :class:`pyalgotrade.stratanalyzer.StrategyAnalyzer`."""
        self.attach_analyzer_ex(strategy_analyzer)

    def get_named_analyzer(self, name):
        return self.__named_analyzers.get(name, None)

    def get_feed(self):
        """Returns the :class:`pyalgotrade.barfeed.BarFeed` that this strategy is using."""
        return self.__feed

    def get_current_date_time(self):
        """Returns the :class:`datetime.datetime` for the current :class:`pyalgotrade.bar.Bar`."""
        ret = None
        bars = self.__feed.get_current_bars()
        if bars:
            ret = bars.get_date_time()
        return ret

    def get_broker(self):
        """Returns the :class:`pyalgotrade.broker.Broker` used to handle order executions."""
        return self.__broker

    def enter_long(self, symbol, quantity, good_until_canceled=False):
        """Generates a buy :class:`pyalgotrade.broker.MarketOrder` to enter a long position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = LongPosition(self, symbol, None, None, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_short(self, symbol, quantity, good_until_canceled=False):
        """Generates a sell short :class:`pyalgotrade.broker.MarketOrder` to enter a short position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = ShortPosition(self, symbol, None, None, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_long_limit(self, symbol, limit_price, quantity, good_until_canceled=False):
        """Generates a buy :class:`pyalgotrade.broker.LimitOrder` to enter a long position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param limit_price: Limit price.
        :type limit_price: float.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = LongPosition(self, symbol, limit_price, None, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_short_position(self, symbol, limit_price, quantity, good_until_canceled=False):
        """Generates a sell short :class:`pyalgotrade.broker.LimitOrder` to enter a short position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param limit_price: Limit price.
        :type limit_price: float.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = ShortPosition(self, symbol, limit_price, None, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_long_stop(self, symbol, stop_price, quantity, good_until_canceled=False):
        """Generates a buy :class:`pyalgotrade.broker.StopOrder` to enter a long position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param stop_price: Stop price.
        :type stop_price: float.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = LongPosition(self, symbol, None, stop_price, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_short_stop(self, symbol, stop_price, quantity, good_until_canceled=False):
        """Generates a sell short :class:`pyalgotrade.broker.StopOrder` to enter a short position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param stop_price: Stop price.
        :type stop_price: float.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = ShortPosition(self, symbol, None, stop_price, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_long_stop_limit(self, symbol, limit_price, stop_price, quantity, good_until_canceled=False):
        """Generates a buy :class:`pyalgotrade.broker.StopLimitOrder` order to enter a long position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param limit_price: Limit price.
        :type limit_price: float.
        :param stop_price: Stop price.
        :type stop_price: float.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = LongPosition(self, symbol, limit_price, stop_price, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def enter_short_stop_limit(self, symbol, limit_price, stop_price, quantity, good_until_canceled=False):
        """Generates a sell short :class:`pyalgotrade.broker.StopLimitOrder` order to enter a short position.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param limit_price: Limit price.
        :type limit_price: float.
        :param stop_price: The Stop price.
        :type stop_price: float.
        :param quantity: Entry order quantity.
        :type quantity: int.
        :param good_until_canceled: True if the entry order is good till canceled. If False then the order gets automatically canceled when the session closes.
        :type good_until_canceled: boolean.
        :rtype: The :class:`Position` entered.
        """

        ret = ShortPosition(self, symbol, limit_price, stop_price, quantity, good_until_canceled)
        self.__register_active_position(ret)
        return ret

    def exit_position(self, position, limit_price=None, stop_price=None, good_until_canceled=None):
        """Generates the exit order for the position.

        :param position: A position returned by any of the enter_longXXX or enter_shortXXX methods.
        :type position: :class:`Position`.
        :param limit_price: The limit price.
        :type limit_price: float.
        :param stop_price: The stop price.
        :type stop_price: float.
        :param good_until_canceled: True if the exit order is good till canceled. If False then the order gets automatically canceled when the session closes. If None, then it will match the entry order.
        :type good_until_canceled: boolean.

        .. note::
            * If the entry order was not filled yet, it will be canceled.
            * If a previous exit order for this position was filled, this won't have any effect.
            * If a previous exit order for this position is pending, it will get canceled and the new exit order submitted.
            * If limit_price is not set and stop_price is not set, then a :class:`pyalgotrade.broker.MarketOrder` is used to exit the position.
            * If limit_price is set and stop_price is not set, then a :class:`pyalgotrade.broker.LimitOrder` is used to exit the position.
            * If limit_price is not set and stop_price is set, then a :class:`pyalgotrade.broker.StopOrder` is used to exit the position.
            * If limit_price is set and stop_price is set, then a :class:`pyalgotrade.broker.StopLimitOrder` is used to exit the position.
        """

        if position.exit_filled():
            return

        # Before exiting a position, the entry order must have been filled.
        if position.get_entry_order().is_filled():
            position.close(limit_price, stop_price, good_until_canceled)
            self.__register_active_position(position)
        else: # If the entry was not filled, cancel it.
            self.get_broker().cancel_order(position.get_entry_order())

    def on_enter_ok(self, position):
        """Override (optional) to get notified when the order submitted to enter a position was filled. The default implementation is empty.

        :param position: A position returned by any of the enter_longXXX or enter_shortXXX methods.
        :type position: :class:`Position`.
        """
        pass

    def on_enter_canceled(self, position):
        """Override (optional) to get notified when the order submitted to enter a position was canceled. The default implementation is empty.

        :param position: A position returned by any of the enter_longXXX or enter_shortXXX methods.
        :type position: :class:`Position`.
        """
        pass

    # Called when the exit order for a position was filled.
    def on_exit_ok(self, position):
        """Override (optional) to get notified when the order submitted to exit a position was filled. The default implementation is empty.

        :param position: A position returned by any of the enter_longXXX or enter_shortXXX methods.
        :type position: :class:`Position`.
        """
        pass

    # Called when the exit order for a position was canceled.
    def on_exit_canceled(self, position):
        """Override (optional) to get notified when the order submitted to exit a position was canceled. The default implementation is empty.

        :param position: A position returned by any of the enter_longXXX or enter_shortXXX methods.
        :type position: :class:`Position`.
        """
        pass

    """Base class for strategies. """
    def on_start(self):
        """Override (optional) to get notified when the strategy starts executing. The default implementation is empty. """
        pass

    def on_finish(self, bars):
        """Override (optional) to get notified when the strategy finished executing. The default implementation is empty.

        :param bars: The last bars processed.
        :type bars: :class:`pyalgotrade.bar.Bars`.
        """
        pass

    def on_bars(self, bars):
        """Override (**mandatory**) to get notified when new bars are available. The default implementation raises an Exception.

        **This is the method to override to enter your trading logic and enter/exit positions**.

        :param bars: The current bars.
        :type bars: :class:`pyalgotrade.bar.Bars`.
        """
        raise NotImplementedError()

    def on_order_updated(self, order):
        """Override (optional) to get notified when an order gets updated. This is only called if the order was placed using the broker interface directly.

        :param order: The order updated.
        :type order: :class:`pyalgotrade.broker.Order`.
        """
        pass

    def __on_order_update(self, broker_, order):
        position = self.__order_to_position.get(order, None)
        if position == None:
            self.on_order_updated(order)
        elif position.get_entry_order() == order:
            if order.is_filled():
                self.on_enter_ok(position)
            elif order.is_canceled():
                self.__unregister_order(position, order)
                self.on_enter_canceled(position)
            else:
                assert(False)
        elif position.get_exit_order() == order:
            if order.is_filled():
                self.__unregister_order(position, order)
                self.on_exit_ok(position)
            elif order.is_canceled():
                self.__unregister_order(position, order)
                self.on_exit_canceled(position)
            else:
                assert(False)
        else:
            # The order used to belong to a position but it was ovewritten with a new one
            # and the previous order should have been canceled.
            assert(order.is_canceled())

    def __check_exit_on_session_close(self, bars):
        for position in self.__active_positions.keys():
            order = position.check_exit_on_session_close(bars)
            if order:
                self.__register_order(position, order)

    def __on_bars(self, bars):
        # THE ORDER HERE IS VERY IMPORTANT

        self.__notify_analyzers(lambda s: s.before_on_bars(self))

        # 1: Let the strategy process current bars and place orders.
        self.on_bars(bars)

        # 2: Place the necessary orders for positions marked to exit on session close.
        self.__check_exit_on_session_close(bars)

        # 3: Notify that the bars were processed.
        self.__bars_processed_event.emit(self, bars)

    def run(self):
        """Call once (**and only once**) to backtest the strategy. """
        try:
            self.__feed.get_new_bars_event().subscribe(self.__on_bars)
            self.__feed.start()
            self.__broker.start()
            self.on_start()

            # Dispatch events as long as the feed or the broker have something to dispatch.
            stop_dispatching_broker = self.__broker.stop_dispatching()
            stop_dispatching_feed = self.__feed.stop_dispatching()
            while not stop_dispatching_feed or not stop_dispatching_broker:
                if not stop_dispatching_broker:
                    self.__broker.dispatch()
                if not stop_dispatching_feed:
                    self.__feed.dispatch()
                stop_dispatching_broker = self.__broker.stop_dispatching()
                stop_dispatching_feed = self.__feed.stop_dispatching()

            if self.__feed.get_current_bars() != None:
                self.on_finish(self.__feed.get_current_bars())
            else:
                raise Exception("Feed was empty")
        finally:
            self.__feed.get_new_bars_event().unsubscribe(self.__on_bars)
            self.__broker.stop()
            self.__feed.stop()
            self.__broker.join()
            self.__feed.join()

