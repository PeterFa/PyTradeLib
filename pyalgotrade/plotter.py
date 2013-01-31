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

import collections

import broker

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib import finance
from matplotlib import dates


def _min(value1, value2):
    if value1 is None:
        return value2
    elif value2 is None:
        return value1
    else:
        return min(value1, value2)

def _max(value1, value2):
    if value1 is None:
        return value2
    elif value2 is None:
        return value1
    else:
        return max(value1, value2)

def _adjustXAxis(mplSubplots):
    minX = None
    maxX = None

    # Calculate min and max x values.
    for mplSubplot in mplSubplots:
        axis = mplSubplot.axis()
        minX = _min(minX, axis[0])
        maxX = _max(maxX, axis[1])

    for mplSubplot in mplSubplots:
        axis = mplSubplot.axis()
        axis = (minX, maxX, axis[2], axis[3])
        mplSubplot.axis(axis)

def _filter_datetimes(date_times, from_date = None, toDate = None):
    class DateTimeFilter:
        def __init__(self, from_date = None, toDate = None):
            self.__from_date = from_date
            self.__toDate = toDate

        def includeDateTime(self, date_time):
            if self.__toDate and date_time > self.__toDate:
                return False
            if self.__from_date and date_time < self.__from_date:
                return False
            return True

    date_timeFilter = DateTimeFilter(from_date, toDate)
    return filter(lambda x: date_timeFilter.includeDateTime(x), date_times)


class Series:
    def __init__(self):
        self.__values = {}

    def getColor(self):
        return None

    def addValue(self, date_time, value):
        self.__values[date_time] = value

    def get_value(self, date_time):
        return self.__values.get(date_time, None)

    def getMarker(self):
        raise NotImplementedError()

    def needColor(self):
        raise NotImplementedError()

    def plot(self, mplSubplot, date_times, color):
        values = []
        for date_time in date_times:
            values.append(self.get_value(date_time))
        mplSubplot.plot(date_times, values, color=color, marker=self.getMarker())


class BuyMarker(Series):
    def getColor(self):
        return 'g'

    def getMarker(self):
        return "^"

    def needColor(self):
        return True


class SellMarker(Series):
    def getColor(self):
        return 'r'

    def getMarker(self):
        return "v"

    def needColor(self):
        return True


class CustomMarker(Series):
    def needColor(self):
        return True

    def getMarker(self):
        return "o"


class LineMarker(Series):
    def needColor(self):
        return True

    def getMarker(self):
        return " "


class InstrumentMarker(Series):
    marker = " "

    def __init__(self):
        Series.__init__(self)
        self.__useCandleSticks = False
        self.__useAdjClose = False

    def needColor(self):
        return self.__useCandleSticks == False

    def getMarker(self):
        return InstrumentMarker.marker

    def setUseAdjClose(self, useAdjClose):
        self.__useAdjClose = useAdjClose

    def get_value(self, date_time):
        # If not using candlesticks, the return the closing price.
        ret = Series.get_value(self, date_time)
        if self.__useCandleSticks == False and ret != None:
            if self.__useAdjClose:
                ret = ret.get_adj_close()
            else:
                ret = ret.get_close()
        return ret

    def plot(self, mplSubplot, date_times, color):
        if self.__useCandleSticks:
            values = []
            for date_time in date_times:
                bar = self.get_value(date_time)
                if bar:
                    values.append( (dates.date2num(date_time), bar.get_open(), bar.get_close(), bar.get_high(), bar.get_low()) )
            finance.candlestick(mplSubplot, values, width=0.5, colorup='g', colordown='r',)
        else:
            Series.plot(self, mplSubplot, date_times, color)


class Subplot:
    """ """
    colors = ['b', 'c', 'm', 'y', 'k']

    def __init__(self):
        self.__series = {} # Series by name.
        self.__dataSeries = {} # Maps a pyalgotrade.dataseries.DataSeries to a Series.
        self.__nextColor = 1

    def __getColor(self, series):
        ret = series.getColor()
        if ret == None:
            ret = Subplot.colors[len(Subplot.colors) % self.__nextColor]
            self.__nextColor += 1
        return ret

    def isEmpty(self):
        return len(self.__series) == 0

    def addDataSeries(self, label, dataSeries):
        """Adds a DataSeries to the subplot.

        :param label: A name for the DataSeries values.
        :type label: string.
        :param dataSeries: The DataSeries to add.
        :type dataSeries: :class:`pyalgotrade.dataseries.DataSeries`.
        """
        self.__dataSeries[dataSeries] = self.getSeries(label)

    def addValuesFromDataSeries(self, date_time):
        for ds, series in self.__dataSeries.iteritems():
            series.addValue(date_time, ds.get_value())

    def getSeries(self, name, defaultClass=LineMarker):
        try:
            ret = self.__series[name]
        except KeyError:
            ret = defaultClass()
            self.__series[name] = ret
        return ret

    def getCustomMarksSeries(self, name):
        return self.getSeries(name, CustomMarker)

    def customizeSubplot(self, mplSubplot):
        # Don't scale the Y axis
        mplSubplot.yaxis.set_major_formatter(ticker.ScalarFormatter(useOffset=False))

    def plot(self, mplSubplot, date_times):
        for series in self.__series.values():
            color = None
            if series.needColor():
                color=self.__getColor(series)
            series.plot(mplSubplot, date_times, color)

        # Legend
        mplSubplot.legend(self.__series.keys(), shadow=True, loc="best")
        self.customizeSubplot(mplSubplot)


class InstrumentSubplot(Subplot):
    """A Subplot responsible for plotting a symbol."""
    def __init__(self, symbol, plotBuySell):
        Subplot.__init__(self)
        self.__symbol = symbol
        self.__plotBuySell = plotBuySell
        self.__symbolSeries = self.getSeries(symbol, InstrumentMarker)

    def setUseAdjClose(self, useAdjClose):
        self.__symbolSeries.setUseAdjClose(useAdjClose)

    def on_bars(self, bars):
        bar = bars.get_bar(self.__symbol)
        if bar:
            date_time = bars.get_date_time()
            self.__symbolSeries.addValue(date_time, bar)

    def on_order_updated(self, broker_, order):
        if self.__plotBuySell and order.is_filled() and order.get_symbol() == self.__symbol:
            action = order.get_action()
            execInfo = order.get_execution_info()
            if action in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
                self.getSeries("Buy", BuyMarker).addValue(execInfo.get_date_time(), execInfo.get_price())
            elif action in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
                self.getSeries("Sell", SellMarker).addValue(execInfo.get_date_time(), execInfo.get_price())


class StrategyPlotter:
    """Class responsible for plotting a strategy execution.

    :param strat: The strategy to plot.
    :type strat: :class:`pyalgotrade.strategy.Strategy`.
    :param plotAllInstruments: Set to True to get a subplot for each symbol available.
    :type plotAllInstruments: boolean.
    :param plotBuySell: Set to True to get the buy/sell events plotted for each symbol available.
    :type plotBuySell: boolean.
    :param plotPortfolio: Set to True to get the portfolio value (shares + cash) plotted.
    :type plotPortfolio: boolean.
    """

    def __init__(self, strat, plotAllInstruments=True, plotBuySell=True, plotPortfolio=True):
        self.__date_times = set()

        self.__plotAllInstruments = plotAllInstruments
        self.__plotBuySell = plotBuySell
        self.__barSubplots = {}
        self.__namedSubplots = collections.OrderedDict()
        self.__portfolioSubplot = None
        if plotPortfolio:
            self.__portfolioSubplot = Subplot()

        strat.get_bars_processed_event().subscribe(self.__on_barsProcessed)
        strat.get_broker().get_order_updated_event().subscribe(self.__on_order_updated)

    def __checkCreateInstrumentSubplot(self, symbol):
        if symbol not in self.__barSubplots:
            self.get_symbolSubplot(symbol)

    def __on_barsProcessed(self, strat, bars):
        date_time = bars.get_date_time()
        self.__date_times.add(date_time)

        if self.__plotAllInstruments:
            for symbol in bars.get_symbols():
                self.__checkCreateInstrumentSubplot(symbol)

        # Notify named subplots.
        for subplot in self.__namedSubplots.values():
            subplot.addValuesFromDataSeries(date_time)

        # Notify bar subplots.
        for subplot in self.__barSubplots.values():
            subplot.on_bars(bars)
            subplot.addValuesFromDataSeries(date_time)

        # Feed the portfolio evolution subplot.
        if self.__portfolioSubplot:
            self.__portfolioSubplot.getSeries("Portfolio").addValue(date_time, strat.get_broker().get_equity())
            # This is in case additional dataseries were added to the portfolio subplot.
            self.__portfolioSubplot.addValuesFromDataSeries(date_time)

    def __on_order_updated(self, broker_, order):
        # Notify BarSubplots
        for subplot in self.__barSubplots.values():
            subplot.on_order_updated(broker_, order)

    def get_symbolSubplot(self, symbol):
        """Returns the InstrumentSubplot for a given symbol

        :rtype: :class:`InstrumentSubplot`.
        """
        try:
            ret = self.__barSubplots[symbol]
        except KeyError:
            ret = InstrumentSubplot(symbol, self.__plotBuySell)
            self.__barSubplots[symbol] = ret
        return ret

    def getOrCreateSubplot(self, name):
        """Returns a Subplot by name. If the subplot doesn't exist, it gets created.

        :param name: The name of the Subplot to get or create.
        :type name: string.
        :rtype: :class:`Subplot`.
        """
        try:
            ret = self.__namedSubplots[name]
        except KeyError:
            ret = Subplot()
            self.__namedSubplots[name] = ret
        return ret

    def getPortfolioSubplot(self):
        """Returns the subplot where the portfolio values get plotted.

        :rtype: :class:`Subplot`.
        """
        return self.__portfolioSubplot

    def plot(self, from_date_time = None, to_date_time = None):
        """Plots the strategy execution. Must be called after running the strategy.

        :param from_date_time: An optional starting datetime.datetime. Everything before it won't get plotted.
        :type from_date_time: datetime.datetime
        :param to_date_time: An optional ending datetime.datetime. Everything after it won't get plotted.
        :type to_date_time: datetime.datetime
        """

        # date_times = [date_time for date_time in self.__date_times]
        date_times = _filter_datetimes(self.__date_times, from_date_time, to_date_time)
        date_times.sort()

        subplots = []
        subplots.extend(self.__barSubplots.values())
        subplots.extend(self.__namedSubplots.values())
        if self.__portfolioSubplot != None:
            subplots.append(self.__portfolioSubplot)

        # Build each subplot.
        fig = plt.figure()
        mplSubplots = []
        subplotIndex = 0
        for subplot in subplots:
            if not subplot.isEmpty():
                mplSubplot = fig.add_subplot(len(subplots), 1, subplotIndex + 1)
                mplSubplots.append(mplSubplot)
                subplot.plot(mplSubplot, date_times)
                mplSubplot.grid(True)
                subplotIndex += 1

        _adjustXAxis(mplSubplots)

        # Display
        plt.show()
