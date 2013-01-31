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

import pyalgotrade.barfeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade import bar
from pyalgotrade.utils import dt

import pytz

import types
import datetime

######################################################################
## NinjaTrader CSV parser
# Each bar must be on its own line and fields must be separated by semicolon (;).
#
# Minute Bars Format:
# yyyyMMdd HHmmss;open price;high price;low price;close price;volume
#
# Daily Bars Format:
# yyyyMMdd;open price;high price;low price;close price;volume
#
# The exported data will be in the UTC time zone.


class Frequency:
    MINUTE = pyalgotrade.barfeed.Frequency.MINUTE
    DAILY = pyalgotrade.barfeed.Frequency.DAY


class RowParser(csvfeed.RowParser):
    def __init__(self, frequency, daily_bar_time, timezone=None):
        self.__frequency = frequency
        self.__daily_bar_time = daily_bar_time
        self.__timezone = timezone

    def __parse_date_time(self, date_time):
        ret = None
        if self.__frequency == pyalgotrade.barfeed.Frequency.MINUTE:
            ret = datetime.datetime.strptime(date_time, "%Y%m%d %H%M%S")
        elif self.__frequency == pyalgotrade.barfeed.Frequency.DAY:
            ret = datetime.datetime.strptime(date_time, "%Y%m%d")
            # Time on CSV files is empty. If told to set one, do it.
            if self.__daily_bar_time != None:
                ret = datetime.datetime.combine(ret, self.__daily_bar_time)
        else:
            assert(False)

        # According to NinjaTrader documentation the exported data will be in UTC.
        ret = pytz.utc.localize(ret)

        # Localize bars if a market session was set.
        if self.__timezone:
            ret = dt.localize(ret, self.__timezone)
        return ret

    def get_field_names(self):
        return ["Date Time", "Open", "High", "Low", "Close", "Volume"]

    def get_delimiter(self):
        return ";"

    def parse_bar(self, csv_row_dict):
        date_time = self.__parse_date_time(csv_row_dict["Date Time"])
        close = float(csv_row_dict["Close"])
        open_ = float(csv_row_dict["Open"])
        high = float(csv_row_dict["High"])
        low = float(csv_row_dict["Low"])
        volume = float(csv_row_dict["Volume"])
        return bar.Bar(date_time, open_, high, low, close, volume, None)


class Feed(csvfeed.BarFeed):
    """A :class:`pyalgotrade.barfeed.csvfeed.BarFeed` that loads bars from CSV files exported from NinjaTrader.

    :param frequency: The frequency of the bars.
    :param timezone: The default timezone to use to localize bars. Check :mod:`pyalgotrade.marketsession`.
    :type timezone: A pytz timezone.

    .. note::

        Valid **frequency** parameter values are:

        * pyalgotrade.barfeed.Frequency.MINUTE
        * pyalgotrade.barfeed.Frequency.DAY
    """

    def __init__(self, frequency, timezone=None):
        if type(timezone) == types.IntType:
            raise Exception("timezone as an int parameter is not supported anymore. Please use a pytz timezone instead.")

        csvfeed.BarFeed.__init__(self, frequency)
        self.__timezone = timezone

    def add_bars_from_csv(self, symbol, path, timezone=None):
        """Loads bars for a given symbol from a CSV formatted file.
        The symbol gets registered in the bar feed.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param path: The path to the file.
        :type path: string.
        :param timezone: The timezone to use to localize bars. Check :mod:`pyalgotrade.marketsession`.
        :type timezone: A pytz timezone.
        """

        if type(timezone) == types.IntType:
            raise Exception("timezone as an int parameter is not supported anymore. Please use a pytz timezone instead.")

        if timezone is None:
            timezone = self.__timezone

        row_parser = RowParser(self.get_frequency(), self.get_daily_bar_time(), timezone)
        csvfeed.BarFeed.add_bars_from_csv(self, symbol, path, row_parser)
