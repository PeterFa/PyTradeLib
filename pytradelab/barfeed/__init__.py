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

from pytradelab import dataseries
from pytradelab import observer
from pytradelab import bar
from pytradelab import warninghelpers

# This class is responsible for:
# - Managing and upating BarDataSeries instances.
# - Event dispatching
#
# Subclasses should implement:
# - get_next_bars
#
# THIS IS A VERY BASIC CLASS AND IN WON'T DO ANY VERIFICATIONS OVER THE BARS RETURNED.

class BasicBarFeed(object):
    def __init__(self, frequency):
        self.__ds = {}
        self.__default_symbol = None
        self.__new_bars_event = observer.Event()
        self.__curent_bars = None
        self.__last_bars = {}
        self.__frequency = frequency

    def __get_next_bars_and_update_ds(self):
        bars = self.get_next_bars()
        if bars != None:
            self.__curent_bars = bars
            # Update self.__last_bars and the dataseries.
            for symbol in bars.get_symbols():
                bar_ = bars.get_bar(symbol)
                self.__last_bars[symbol] = bar_
                self.__ds[symbol].append_value(bar_)
        return bars

    def __iter__(self):
        return self

    def next(self):
        if self.stop_dispatching():
            raise StopIteration()
        return self.__get_next_bars_and_update_ds()

    def get_frequency(self):
        return self.__frequency

    def get_current_bars(self):
        """Returns the current :class:`pytradelab.bar.Bars`."""
        return self.__curent_bars

    def get_last_bars(self):
        warninghelpers.deprecation_warning("get_last_bars will be deprecated in the next version. Please use get_current_bars instead.", stacklevel=2)
        return self.get_current_bars()

    def get_last_bar(self, symbol):
        """Returns the last :class:`pytradelab.bar.Bar` for a given symbol, or None."""
        return self.__last_bars.get(symbol, None)

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def join(self):
        raise NotImplementedError()

    # Return True if there are not more events to dispatch.
    def stop_dispatching(self):
        raise NotImplementedError()

    # Subclasses should implement this and return a pytradelab.bar.Bars or None if there are no bars.
    def get_next_bars(self):
        raise NotImplementedError()

    def get_new_bars_event(self):
        return self.__new_bars_event

    def get_default_symbol(self):
        """Returns the default symbol."""
        return self.__default_symbol

    # Dispatch events.
    def dispatch(self):
        bars = self.__get_next_bars_and_update_ds()
        if bars != None:
            self.__new_bars_event.emit(bars)

    def get_registered_symbols(self):
        """Returns a list of registered intstrument names."""
        return self.__ds.keys()

    def register_symbol(self, symbol):
        self.__default_symbol = symbol
        if symbol not in self.__ds:
            self.__ds[symbol] = dataseries.BarDataSeries()

    def get_data_series(self, symbol = None):
        """Returns the :class:`pytradelab.dataseries.BarDataSeries` for a given symbol.

        :param symbol: Instrument identifier. If None, the default symbol is returned.
        :type symbol: string.
        :rtype: :class:`pytradelab.dataseries.BarDataSeries`.
        """
        if symbol == None:
            symbol = self.__default_symbol
        return self.__ds[symbol]

    def __getitem__(self, symbol):
        """Returns the :class:`pytradelab.dataseries.BarDataSeries` for a given symbol.
        If the symbol is not found an exception is raised."""
        return self.__ds[symbol]

    def __contains__(self, symbol):
        """Returns True if a :class:`pytradelab.dataseries.BarDataSeries` for the given symbol is available."""
        return symbol in self.__ds

# This class is responsible for:
# - Checking the pytradelab.bar.Bar objects returned by fetch_next_bars and building pytradelab.bar.Bars objects.
#
# Subclasses should implement:
# - fetch_next_bars

class BarFeed(BasicBarFeed):
    """Base class for :class:`pytradelab.bar.Bars` providing feeds.

    :param frequency: The bars frequency.
    :type frequency: bar.Frequency.MINUTE or bar.Frequency.DAY.

    .. note::
        This is a base class and should not be used directly.
    """
    def __init__(self, frequency):
        BasicBarFeed.__init__(self, frequency)
        self.__prev_date_time = None

    # Override to return a map from symbol names to bars or None if there is no data. All bars datetime must be equal.
    def fetch_next_bars(self):
        raise NotImplementedError()

    def get_next_bars(self):
        """Returns the next :class:`pytradelab.bar.Bars` in the feed or None if there are no bars."""

        bar_dict = self.fetch_next_bars()
        if bar_dict == None:
            return None

        # This will check for incosistent datetimes between bars.
        ret = bar.Bars(bar_dict)

        # Check that current bar datetimes are greater than the previous one.
        if self.__prev_date_time != None and self.__prev_date_time >= ret.get_date_time():
            raise Exception("Bar data times are not in order. Previous datetime was %s and current datetime is %s" % (self.__prev_date_time, ret.get_date_time()))
        self.__prev_date_time = ret.get_date_time()

        return ret

# This class is used by the optimizer module. The barfeed is already built on the server side, and the bars are sent back to workers.
class OptimizerBarFeed(BasicBarFeed):
    def __init__(self, frequency, symbols, bars):
        BasicBarFeed.__init__(self, frequency)
        for symbol in symbols:
            self.register_symbol(symbol)
        self.__bars = bars
        self.__next_bar = 0

    def start(self):
        pass

    def stop(self):
        pass

    def join(self):
        pass

    def get_next_bars(self):
        ret = None
        if self.__next_bar < len(self.__bars):
            ret = self.__bars[self.__next_bar]
            self.__next_bar += 1
        return ret

    def stop_dispatching(self):
        return self.__next_bar >= len(self.__bars)
