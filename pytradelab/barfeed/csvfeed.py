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

from pytradelab import bar
from pytradelab import barfeed
from pytradelab import warninghelpers
from pytradelab.utils import dt
from pytradelab.barfeed import membf

import csv
import datetime
import types
import pytz


# Interface for csv row parsers.
class RowParser(object):
    def parse_bar(self, csv_row_dict):
        raise Exception("Not implemented")

    def get_field_names(self):
        raise Exception("Not implemented")

    def get_delimiter(self):
        raise Exception("Not implemented")


# Interface for bar filters.
class BarFilter(object):
    def include_bar(self, bar_):
        raise Exception("Not implemented")


class DateRangeFilter(BarFilter):
    def __init__(self, from_date=None, to_date=None):
        self.__from_date = from_date
        self.__to_date = to_date

    def include_bar(self, bar_):
        if self.__to_date and bar_.get_date_time() > self.__to_date:
            return False
        if self.__from_date and bar_.get_date_time() < self.__from_date:
            return False
        return True


# US Equities Regular Trading Hours filter
# Monday ~ Friday
# 9:30 ~ 16 (GMT-5)
class USEquitiesRTH(DateRangeFilter):
    timezone = pytz.timezone("US/Eastern")

    def __init__(self, from_date = None, to_date = None):
        DateRangeFilter.__init__(self, from_date, to_date)

        self.__from_time = datetime.time(9, 30, 0)
        self.__to_time = datetime.time(16, 0, 0)

    def include_bar(self, bar_):
        ret = DateRangeFilter.include_bar(self, bar_)
        if ret:
            # Check day of week
            barDay = bar_.get_date_time().weekday()
            if barDay > 4:
                return False

            # Check time
            barTime = dt.localize(bar_.get_date_time(), USEquitiesRTH.timezone).time()
            if barTime < self.__from_time:
                return False
            if barTime > self.__to_time:
                return False
        return ret


class BarFeed(membf.Feed):
    """A CSV file based :class:`pytradelab.barfeed.BarFeed`.

    .. note::
        This is a base class and should not be used directly.
    """

    def __init__(self, frequency):
        membf.Feed.__init__(self, frequency)
        self.__bar_filter = None
        self.__daily_time = datetime.time(23, 59, 59)

    def get_daily_bar_time(self):
        """Returns the time to set to daily bars when that information is not present in CSV files. Defaults to 23:59:59.

        :rtype: datetime.time.
        """
        return self.__daily_time

    def set_daily_bar_time(self, time):
        """Sets the time to set to daily bars when that information is not present in CSV files.

        :param time: The time to set.
        :type time: datetime.time.
        """
        self.__daily_time = time

    def set_bar_filter(self, bar_filter):
        self.__bar_filter = bar_filter

    def add_bars_from_csv(self, symbol, path, row_parser):
        # Load the csv file
        loaded_bars = []
        reader = csv.DictReader(open(path, "r"), fieldnames=row_parser.get_field_names(), delimiter=row_parser.get_delimiter())
        for row in reader:
            bar_ = row_parser.parse_bar(row)
            if bar_ != None and (self.__bar_filter is None or self.__bar_filter.include_bar(bar_)):
                loaded_bars.append(bar_)

        self.add_bars_from_sequence(symbol, loaded_bars)


######################################################################
## Yahoo CSV parser
# Each bar must be on its own line and fields must be separated by comma (,).
#
# Bars Format:
# Date,Open,High,Low,Close,Volume,Adj Close
#
# The csv Date column must have the following format: YYYY-MM-DD

class YahooRowParser(RowParser):
    def __init__(self, daily_bar_time, timezone = None):
        self.__daily_bar_time = daily_bar_time
        self.__timezone = timezone

    def __parse_date(self, date_str):
        ret = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        # Time on Yahoo! Finance CSV files is empty. If told to set one, do it.
        if self.__daily_bar_time != None:
            ret = datetime.datetime.combine(ret, self.__daily_bar_time)
        # Localize the datetime if a timezone was given.
        if self.__timezone:
            ret = dt.localize(ret, self.__timezone)
        return ret

    def get_field_names(self):
        # It is expected for the first row to have the field names.
        return None

    def get_delimiter(self):
        return ","

    def parse_bar(self, csv_row_dict):
        date_time = self.__parse_date(csv_row_dict["Date"])
        close = float(csv_row_dict["Close"])
        open_ = float(csv_row_dict["Open"])
        high = float(csv_row_dict["High"])
        low = float(csv_row_dict["Low"])
        volume = float(csv_row_dict["Volume"])
        adj_close = float(csv_row_dict["Adj Close"])
        return bar.Bar(date_time, open_, high, low, close, volume, adj_close)


class YahooFeed(BarFeed):
    def __init__(self, timezone=None, skip_warning=False):
        if type(timezone) == types.IntType:
            raise Exception("timezone as an int parameter is not supported anymore. Please use a pytz timezone instead.")

        if not skip_warning:
            warninghelpers.deprecation_warning("pytradelab.barfeed.csvfeed.YahooFeed will be deprecated in the next version. Please use pytradelab.barfeed.yahoofeed.Feed instead.", stacklevel=2)

        BarFeed.__init__(self, bar.Frequency.DAY)
        self.__timezone = timezone
    
    def add_bars_from_csv(self, symbol, path, timezone = None):
        if type(timezone) == types.IntType:
            raise Exception("timezone as an int parameter is not supported anymore. Please use a pytz timezone instead.")

        if timezone is None:
            timezone = self.__timezone
        row_parser = YahooRowParser(self.get_daily_bar_time(), timezone)
        BarFeed.add_bars_from_csv(self, symbol, path, row_parser)
