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

from pyalgotrade import stratanalyzer
from pyalgotrade import broker
from pyalgotrade.stratanalyzer import returns

import numpy as np


class Trades(stratanalyzer.StrategyAnalyzer):
    """A :class:`pyalgotrade.stratanalyzer.StrategyAnalyzer` that records the profit/loss
    and returns of every completed trade.

    .. note::
        This analyzer operates on individual completed trades.
        For example, lets say you start with a $1000 cash, and then you buy 1 share of XYZ
        for $10 and later sell it for $20:

            * The trade's profit was $10.
            * The trade's return is 100%, even though your whole portfolio went from $1000 to $1020, a 2% return.
    """
    def __init__(self):
        self.__all = []
        self.__profits = []
        self.__losses = []
        self.__all_returns = []
        self.__positive_returns = []
        self.__negative_returns = []
        self.__all_commissions = []
        self.__profitable_commissions = []
        self.__unprofitable_commissions = []
        self.__even_commissions = []
        self.__even_trades = 0
        self.__position_trackers = {}

    def __update_trades(self, position_tracker):
        price = 0 # The price doesn't matter since the position should be closed.
        assert(position_tracker.get_shares() == 0)
        net_profit =  position_tracker.get_net_profit(price)
        net_return =  position_tracker.get_return(price)

        if net_profit > 0:
            self.__profits.append(net_profit)
            self.__positive_returns.append(net_return )
            self.__profitable_commissions.append(position_tracker.get_commissions())
        elif net_profit < 0:
            self.__losses.append(net_profit)
            self.__negative_returns.append(net_return )
            self.__unprofitable_commissions.append(position_tracker.get_commissions())
        else:
            self.__even_trades += 1
            self.__even_commissions.append(position_tracker.get_commissions())

        self.__all.append(net_profit)
        self.__all_returns.append(net_return)
        self.__all_commissions.append(position_tracker.get_commissions())

        position_tracker.update(price)

    def __update_position_tracker(self, position_tracker, price, commission, quantity):
        current_shares = position_tracker.get_shares()

        if current_shares > 0: # Current position is long
            if quantity > 0: # Increase long position
                position_tracker.buy(quantity, price, commission)
            else:
                new_shares = current_shares + quantity
                if new_shares == 0: # Exit long.
                    position_tracker.sell(current_shares, price, commission)
                    self.__update_trades(position_tracker)
                elif new_shares > 0: # Sell some shares.
                    position_tracker.sell(quantity*-1, price, commission)
                else: # Exit long and enter short. Use proportional commissions.
                    position_tracker.sell(current_shares, price, commission / float(current_shares))
                    self.__update_trades(position_tracker)
                    position_tracker.sell(new_shares*-1, price, commission / float(new_shares*-1))
        elif current_shares < 0: # Current position is short
            if quantity < 0: # Increase short position
                position_tracker.sell(quantity*-1, price, commission)
            else:
                new_shares = current_shares + quantity
                if new_shares == 0: # Exit short.
                    position_tracker.buy(current_shares*-1, price, commission)
                    self.__update_trades(position_tracker)
                elif new_shares < 0: # Re-buy some shares.
                    position_tracker.buy(quantity, price, commission)
                else: # Exit short and enter long. Use proportional commissions.
                    position_tracker.buy(current_shares*-1, price, commission / float(current_shares*-1))
                    self.__update_trades(position_tracker)
                    position_tracker.buy(new_shares, price, commission / float(new_shares))
        elif quantity > 0:
            position_tracker.buy(quantity, price, commission)
        else:
            position_tracker.sell(quantity*-1, price, commission)

    def __on_order_update(self, broker_, order):
        # Only interested in filled orders.
        if not order.is_filled():
            return

        # Get or create the tracker for this symbol.
        try:
            position_tracker = self.__position_trackers[order.get_symbol()]
        except KeyError:
            position_tracker = returns.PositionTracker()
            self.__position_trackers[order.get_symbol()] = position_tracker

        # Update the tracker for this order.
        price = order.get_execution_info().get_price()
        commission = order.get_execution_info().get_commission()
        action = order.get_action()
        if action in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
            quantity = order.get_execution_info().get_quantity()
        elif action in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
            quantity = order.get_execution_info().get_quantity() * -1
        else: # Unknown action
            assert(False)

        self.__update_position_tracker(position_tracker, price, commission, quantity)

    def attached(self, strat):
        strat.get_broker().get_order_updated_event().subscribe(self.__on_order_update)

    def get_count(self):
        """Returns the total number of trades."""
        return len(self.__all)

    def get_profitable_count(self):
        """Returns the number of profitable trades."""
        return len(self.__profits)

    def get_unprofitable_count(self):
        """Returns the number of unprofitable trades."""
        return len(self.__losses)

    def get_even_count(self):
        """Returns the number of trades whose net profit was 0."""
        return self.__even_trades

    def get_all(self):
        """Returns a numpy.array with the profits/losses for each trade."""
        return np.array(self.__all)

    def get_profits(self):
        """Returns a numpy.array with the profits for each profitable trade."""
        return np.array(self.__profits)

    def get_losses(self):
        """Returns a numpy.array with the losses for each unprofitable trade."""
        return np.array(self.__losses)

    def get_all_returns(self):
        """Returns a numpy.array with the returns for each trade."""
        return np.array(self.__all_returns)

    def get_positive_returns(self):
        """Returns a numpy.array with the positive returns for each trade."""
        return np.array(self.__positive_returns)

    def get_negative_returns(self):
        """Returns a numpy.array with the negative returns for each trade."""
        return np.array(self.__negative_returns)

    def get_commissions_for_all_trades(self):
        """Returns a numpy.array with the commissions for each trade."""
        return np.array(self.__all_commissions)

    def get_commissions_for_profitable_trades(self):
        """Returns a numpy.array with the commissions for each profitable trade."""
        return np.array(self.__profitable_commissions)

    def get_commissions_for_unprofitable_trades(self):
        """Returns a numpy.array with the commissions for each unprofitable trade."""
        return np.array(self.__unprofitable_commissions)

    def get_commissions_for_even_trades(self):
        """Returns a numpy.array with the commissions for each trade whose net profit was 0."""
        return np.array(self.__even_commissions)
