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

from pytradelab import strategy
from pytradelab.technical import ma
from pytradelab.technical import rsi


class Strategy(strategy.Strategy):
    def __init__(self, feed, entrySMA, exitSMA, rsiPeriod, overBoughtThreshold, overSoldThreshold):
        initialCash = 2000
        strategy.Strategy.__init__(self, feed, initialCash)
        self.__symbol = feed.get_default_symbol()
        ds = feed.get_data_series().get_close_data_series()
        self.__entrySMA = ma.SMA(ds, entrySMA)
        self.__exitSMA = ma.SMA(ds, exitSMA)
        self.__rsi = rsi.RSI(ds, rsiPeriod)
        self.__overBoughtThreshold = overBoughtThreshold
        self.__overSoldThreshold = overSoldThreshold
        self.__longPos = None
        self.__shortPos = None

    def on_enter_canceled(self, position):
        if self.__longPos == position:
            self.__longPos = None
        elif self.__shortPos == position:
            self.__shortPos = None
        else:
            assert(False)

    def on_exit_ok(self, position):
        if self.__longPos == position:
            self.__longPos = None
        elif self.__shortPos == position:
            self.__shortPos = None
        else:
            assert(False)

    def on_exit_canceled(self, position):
        # If the exit was canceled, re-submit it.
        self.exit_position(position)

    def on_bars(self, bars):
        # Wait for enough bars to be available to calculate SMA and RSI.
        if self.__exitSMA[-1] is None or self.__entrySMA[-1] is None or self.__rsi[-1] is None:
            return

        bar = bars.get_bar(self.__symbol)
        if self.__longPos != None:
            if self.exitLongSignal(bar):
                self.exit_position(self.__longPos)
        elif self.__shortPos != None:
            if self.exitShortSignal(bar):
                self.exit_position(self.__shortPos)
        else:
            if self.enter_longSignal(bar):
                self.__longPos = self.enter_long(self.__symbol, 10, True)
            elif self.enter_shortSignal(bar):
                self.__shortPos = self.enter_short(self.__symbol, 10, True)

    def enter_longSignal(self, bar):
        return bar.get_close() > self.__entrySMA[-1] and self.__rsi[-1] <= self.__overSoldThreshold

    def exitLongSignal(self, bar):
        return bar.get_close() > self.__exitSMA[-1]

    def enter_shortSignal(self, bar):
        return bar.get_close() < self.__entrySMA[-1] and self.__rsi[-1] >= self.__overBoughtThreshold

    def exitShortSignal(self, bar):
        return bar.get_close() < self.__exitSMA[-1]
