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

from pytradelab import stratanalyzer
from pytradelab import observer
from pytradelab import dataseries


# Helper class to calculate returns and net profit.
class PositionTracker(object):
    def __init__(self):
        self.__shares = 0
        self.__cash = 0
        self.__commissions = 0
        self.__cost = 0

    def __update_cost(self, quantity, price):
        cost = 0

        if self.__shares > 0: # Current position is long
            if quantity > 0: # Increase long position
                cost = quantity * price
            else:
                diff = self.__shares + quantity
                if diff < 0: # Entering a short position
                    cost = abs(diff) * price
        elif self.__shares < 0: # Current position is short
            if quantity < 0: # Increase short position
                cost = abs(quantity) * price
            else:
                diff = self.__shares + quantity
                if diff > 0: # Entering a long position
                    cost = diff * price
        else:
            cost = abs(quantity) * price
        self.__cost += cost

    def get_shares(self):
        return self.__shares

    def get_cost(self):
        return self.__cost

    def get_commissions(self):
        return self.__commissions

    def get_net_profit(self, price, include_commissions=True):
        ret = self.__cash + self.__shares * price
        if include_commissions:
            ret -= self.__commissions
        return ret

    def get_return(self, price, include_commissions=True):
        ret = 0
        net_profit = self.get_net_profit(price, include_commissions)
        cost = self.get_cost()
        if cost != 0:
            ret = net_profit / float(cost)
        return ret

    def buy(self, quantity, price, commission=0):
        assert(quantity > 0)
        self.__update_cost(quantity, price)
        self.__cash += quantity * -1 * price
        self.__shares += quantity
        self.__commissions += commission

    def sell(self, quantity, price, commission=0):
        assert(quantity > 0)
        self.__update_cost(quantity * -1, price)
        self.__cash += quantity * price
        self.__shares -= quantity
        self.__commissions += commission

    def update(self, price):
        self.__commissions = 0
        self.__cash = self.__shares * -1 * price
        self.__cost = abs(self.__shares) * price


class ReturnsAnalyzerBase(stratanalyzer.StrategyAnalyzer):
    def __init__(self):
        self.__net_return = 0
        self.__cumulative_return = 0
        self.__event = observer.Event()
        self.__last_portfolio_value = None

    @classmethod
    def get_or_create_shared(cls, strat):
        name = cls.__name__
        # Get or create the shared ReturnsAnalyzerBase.
        ret = strat.get_named_analyzer(name)
        if ret == None:
            ret = ReturnsAnalyzerBase()
            strat.attach_analyzer_ex(ret, name)
        return ret

    def attached(self, strat):
        self.__last_portfolio_value = strat.get_broker().get_equity()

    # An event will be notified when return are calculated at each bar. The hander should receive 1 parameter:
    # 1: This analyzer's instance
    def get_event(self):
        return self.__event

    def get_net_return(self):
        return self.__net_return

    def get_cumulative_return(self):
        return self.__cumulative_return

    def before_on_bars(self, strat):
        current_portfolio_value = strat.get_broker().get_equity()
        net_return = (current_portfolio_value - self.__last_portfolio_value) / float(self.__last_portfolio_value)
        self.__last_portfolio_value = current_portfolio_value
        self.__net_return = net_return

        # Calculate cumulative return.
        self.__cumulative_return = (1 + self.__cumulative_return) * (1 + net_return) - 1

        # Notify that new returns are available.
        self.__event.emit(self)


class Returns(stratanalyzer.StrategyAnalyzer):
    """A :class:`pytradelab.stratanalyzer.StrategyAnalyzer` that calculates
    returns and cumulative returns for the whole portfolio."""

    def __init__(self):
        self.__net_returns = dataseries.SequenceDataSeries()
        self.__cumulative_returns = dataseries.SequenceDataSeries()

    def before_attach(self, strat):
        # Get or create a shared ReturnsAnalyzerBase
        analyzer = ReturnsAnalyzerBase.get_or_create_shared(strat)
        analyzer.get_event().subscribe(self.__on_returns)

    def __on_returns(self, returns_analyzer_base):
        self.__net_returns.append_value(returns_analyzer_base.get_net_return())
        self.__cumulative_returns.append_value(returns_analyzer_base.get_cumulative_return())

    def get_returns(self):
        """Returns a :class:`pytradelab.dataseries.DataSeries` with the returns for each bar."""
        return self.__net_returns

    def get_cumulative_returns(self):
        """Returns a :class:`pytradelab.dataseries.DataSeries` with the cumulative returns for each bar."""
        return self.__cumulative_returns
