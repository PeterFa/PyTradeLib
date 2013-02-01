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

class Frequency:
    MINUTE = 1
    FIVE = 5
    TEN = 10
    FIFTEEN = 15
    THIRTY = 30
    HOUR = 60
    DAY = 'd'
    WEEK = 'w'
    MONTH = 'm'


class Bar(object):
    """A symbol's prices at a given time.

    :param date_time: The date time.
    :type date_time: datetime.datetime
    :param open_: The opening price.
    :type open_: float
    :param high: The highest price.
    :type high: float
    :param low: The lowest price.
    :type low: float
    :param close: The closing price.
    :type close: float
    :param volume: The volume.
    :type volume: float
    :param adj_close: The adjusted closing price.
    :type adj_close: float
    """

    def __init__(self, date_time, open_, high, low, close, volume, adj_close):
        assert(high >= open_)
        assert(high >= low)
        assert(high >= close)
        assert(low <= open_)
        assert(low <= high)
        assert(low <= close)

        self.__date_time = date_time
        self.__open = open_
        self.__close = close
        self.__high = high
        self.__low = low
        self.__volume = volume
        self.__adj_close = adj_close
        self.__session_close = False
        self.__bars_until_session_close = None

    def get_date_time(self):
        """Returns the :class:`datetime.datetime`."""
        return self.__date_time

    def get_open(self):
        """Returns the opening price."""
        return self.__open

    def get_high(self):
        """Returns the highest price."""
        return self.__high

    def get_low(self):
        """Returns the lowest price."""
        return self.__low

    def get_close(self):
        """Returns the closing price."""
        return self.__close

    def get_volume(self):
        """Returns the volume."""
        return self.__volume

    def get_adj_open(self):
        return self.__adj_close * self.__open / float(self.__close)

    def get_adj_high(self):
        return self.__adj_close * self.__high / float(self.__close)

    def get_adj_low(self):
        return self.__adj_close * self.__low / float(self.__close)

    def get_adj_close(self):
        """Returns the adjusted closing price."""
        return self.__adj_close

    def get_session_close(self):
        # Returns True if this is the last bar for the session, or False otherwise.
        return self.__session_close

    def set_session_close(self, session_close):
        self.__session_close = session_close
        if session_close:
            self.__bars_until_session_close = 0

    def get_bars_until_session_close(self):
        return self.__bars_until_session_close

    def set_bars_until_session_close(self, bars_until_session_close):
        self.__bars_until_session_close = bars_until_session_close

class Bars(object):
    """A group of :class:`Bar` objects.

    :param bar_dict: A map of symbol to :class:`Bar` objects.
    :type bar_dict: map.

    .. note::
        All bars must have the same datetime.
    """
    def __init__(self, bar_dict):
        if len(bar_dict) == 0:
            raise Exception("No bars supplied")

        # Check that bar datetimes are in sync
        first_date_time = None
        first_symbol = None
        for symbol, current_bar in bar_dict.iteritems():
            if first_date_time is None:
                first_date_time = current_bar.get_date_time()
                first_symbol = symbol
            elif current_bar.get_date_time() != first_date_time:
                raise Exception(
                    "Bar data times are not in sync. %s %s != %s %s" % (
                        symbol, current_bar.get_date_time(), first_symbol, first_date_time))

        self.__bar_dict = bar_dict
        self.__date_time = first_date_time

    def __getitem__(self, symbol):
        """Returns the :class:`pytradelab.bar.Bar` for the given symbol. If the symbol is not found an exception is raised."""
        return self.__bar_dict[symbol]

    def __contains__(self, symbol):
        """Returns True if a :class:`pytradelab.bar.Bar` for the given symbol is available."""
        return symbol in self.__bar_dict

    def get_symbols(self):
        """Returns the symbol symbols."""
        return self.__bar_dict.keys()

    def get_date_time(self):
        """Returns the :class:`datetime.datetime` for this set of bars."""
        return self.__date_time

    def get_bar(self, symbol):
        """Returns the :class:`pytradelab.bar.Bar` for the given symbol or None if the symbol is not found."""
        return self.__bar_dict.get(symbol, None)
