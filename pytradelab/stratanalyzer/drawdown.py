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


class DrawDownHelper(object):
    def __init__(self, initial_value):
        self.__high_water_mark = initial_value
        self.__low_water_mark = initial_value
        self.__last_low = initial_value
        self.__duration = 0

    # The drawdown duration, not necessarily the max drawdown duration.
    def get_duration(self):
        return self.__duration

    def get_max_draw_down(self):
        return (self.__low_water_mark - self.__high_water_mark) / float(self.__high_water_mark)

    def get_current_draw_down(self):
        return (self.__last_low - self.__high_water_mark) / float(self.__high_water_mark)

    def update(self, low, high):
        assert(low <= high)
        self.__last_low = low
        if high < self.__high_water_mark:
            self.__duration += 1
            self.__low_water_mark = min(self.__low_water_mark, low)
        else:
            self.__high_water_mark = high
            self.__low_water_mark = low
            if low == high:
                self.__duration = 0
            else:
                self.__duration = 1


class DrawDown(stratanalyzer.StrategyAnalyzer):
    """A :class:`pytradelab.stratanalyzer.StrategyAnalyzer` that calculates
    max. drawdown and longest drawdown duration for the portfolio."""

    def __init__(self):
        self.__max_draw_down = 0
        self.__longest_draw_down_duration = 0
        self.__current_draw_down = None

    def attached(self, strat):
        self.__current_draw_down = DrawDownHelper(self.calculate_equity(strat))

    def calculate_equity(self, strat):
        return strat.get_broker().get_equity()
        # ret = strat.get_broker().get_cash()
        # for symbol, shares in strat.get_broker().get_positions().iteritems():
        # 	_bar = strat.get_feed().get_last_bar(symbol)
        # 	if shares > 0:
        # 		ret += strat.get_broker().get_bar_low(_bar) * shares
        # 	elif shares < 0:
        # 		ret += strat.get_broker().get_bar_high(_bar) * shares
        # return ret

    def before_on_bars(self, strat):
        equity = self.calculate_equity(strat)
        self.__current_draw_down.update(equity, equity)
        self.__longest_draw_down_duration = max(self.__longest_draw_down_duration, self.__current_draw_down.get_duration())
        self.__max_draw_down = min(self.__max_draw_down, self.__current_draw_down.get_max_draw_down())

    def get_max_draw_down(self):
        """Returns the max. (deepest) drawdown."""
        return abs(self.__max_draw_down)

    def get_longest_draw_down_duration(self):
        """Returns the duration of the longest drawdown.

        .. note::
            Note that this is the duration of the longest drawdown, not necessarily the deepest one.
        """
        return self.__longest_draw_down_duration
