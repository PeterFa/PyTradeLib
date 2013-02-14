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

from pytradelib import stratanalyzer
from pytradelib.stratanalyzer import returns
from pytradelib.utils import stats

import math


def sharpe_ratio(returns, risk_free_rate, trading_periods, annualized=True):
    ret = 0.0

    # From http://en.wikipedia.org/wiki/Sharpe_ratio: if Rf is a constant risk-free return throughout the period,
    # then stddev(R - Rf) = stddev(R).
    volatility = stats.stddev(returns, 1)

    if volatility != 0:
        excess_returns = [daily_return - (risk_free_rate/float(trading_periods)) for daily_return in returns]
        average_excess_returns = stats.mean(excess_returns)
        ret = average_excess_returns / volatility
        if annualized:
            ret = ret * math.sqrt(trading_periods)
    return ret


class SharpeRatio(stratanalyzer.StrategyAnalyzer):
    """A :class:`pytradelib.stratanalyzer.StrategyAnalyzer` that calculates
    Sharpe ratio for the whole portfolio."""
    def __init__(self):
        self.__net_returns = []

    def before_attach(self, strat):
        # Get or create a shared ReturnsAnalyzerBase
        analyzer = returns.ReturnsAnalyzerBase.get_or_create_shared(strat)
        analyzer.get_event().subscribe(self.__on_returns)

    def __on_returns(self, returns_analyzer_base):
        self.__net_returns.append(returns_analyzer_base.get_net_return())

    def get_sharpe_ratio(self, risk_free_rate, trading_periods, annualized=True):
        """
        Returns the Sharpe ratio for the strategy execution.
        If the volatility is 0, 0 is returned.

        :param risk_free_rate: The risk free rate per annum.
        :type risk_free_rate: int/float.
        :param trading_periods: The number of trading periods per annum.
        :type trading_periods: int/float.
        :param annualized: True if the sharpe ratio should be annualized.
        :type annualized: boolean.

        .. note::
            * If using daily bars, trading_periods should be set to 252.
            * If using hourly bars (with 6.5 trading hours a day) then trading_periods should be set to 252 * 6.5 = 1638.
        """
        return sharpe_ratio(self.__net_returns, risk_free_rate, trading_periods, annualized)
