# This file's contents were originally parts of PyAlgoTrade.
#
# Copyright 2011-2012 Gabriel Martin Becedillas Ruiz
# Copyright 2013 Brian A Cappello
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
.. moduleauthor:: Brian A Cappello <briancappello@gmail>
"""

import pytz
import datetime

from pytradelab import bar
from pytradelab import observer
from pytradelab import dataseries
from pytradelab import warninghelpers
from pytradelab.barfeed import helpers


# Interface for bar filters.
class Filter(object):
    def include_bar(self, bar_):
        raise Exception("Not implemented")


class DateRangeFilter(Filter):
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
    def __init__(self, from_date=None, to_date=None):
        DateRangeFilter.__init__(self, from_date, to_date)
        self.timezone = pytz.timezone("US/Eastern")
        
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
            barTime = dt.localize(bar_.get_date_time(), self.timezone).time()
            if barTime < self.__from_time:
                return False
            if barTime > self.__to_time:
                return False
        return ret

# Calculates session close based on days.
# When the current bar is the last bar for the day, or the last bar in the feed, the session is closed.
def session_close(current_bar, next_bar):
    ret = False
    if next_bar == None:
        ret = True
    elif current_bar.get_date_time().date() != next_bar.get_date_time().date():
        ret = True
    return ret

# Sets session close and bars till session close properties to bars in a sequence. 
def set_session_close_attributes(bar_seq, session_close_strategy=None):
    for i in xrange(1, len(bar_seq)):
        if session_close(bar_seq[i-1], bar_seq[i]):
            bar_seq[i-1].set_session_close(True)
            # Flag the penultimate bar if:
            # - There is a penultimate bar
            # - The penultimate and last bar belong to the same session.
            if i-2 >= 0 and session_close(bar_seq[i-2], bar_seq[i-1]) == False:
                bar_seq[i-2].set_bars_until_session_close(1)

    # Deal with the last bars in the feed.
    if len(bar_seq):
        bar_seq[-1].set_session_close(True)
        if len(bar_seq) > 1:
            bar_seq[-2].set_bars_until_session_close(1)


# This class is responsible for:
# - Holding bars in memory. FIXME generators!!
# - Aligning them with respect to time.
# - Event dispatching
# - Building pytradelab.bar.Bars objects for get_bars(bars_ago=0) and get_next_bars()

class BarFeed(object):
    def __init__(self, frequency):
        self.__frequency = frequency
        self.__ds = {}
        self.__bars = {}
        self.__started = False
        self.__bars_left = 0
        self.__next_bar_idx = {}
        self.__prev_date_time = None
        self.__new_bars_event = observer.Event()

    def get_frequency(self):
        return self.__frequency

    def add_bars_from_sequence(self, symbol, bars):
        if self.__started:
            raise Exception("Can't add more bars once you started consuming bars")
        self.__bars.setdefault(symbol, [])
        self.__next_bar_idx.setdefault(symbol, 0)

        # Add and sort the bars
        self.__bars[symbol].extend(bars)
        barCmp = lambda x, y: cmp(x.get_date_time(), y.get_date_time())
        self.__bars[symbol].sort(barCmp)
        if symbol not in self.__ds:
            self.__ds[symbol] = dataseries.BarDataSeries()

    def get_new_bars_event(self):
        return self.__new_bars_event

    def get_data_series(self, symbol):
        """Returns the :class:`pytradelab.dataseries.BarDataSeries` for the given
        symbol.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :rtype: :class:`pytradelab.dataseries.BarDataSeries`.
        """
        return self.__ds[symbol]

    def keys(self):
        """Returns a list of registered symbol names."""
        return self.__ds.keys()

    def __getitem__(self, symbol):
        """Returns the :class:`pytradelab.dataseries.BarDataSeries` for a given
        symbol. If the symbol is not found an exception is raised."""
        return self.__ds[symbol]

    def __contains__(self, symbol):
        """Returns True if a :class:`pytradelab.dataseries.BarDataSeries` for
        the given symbol is available."""
        return symbol in self.__ds

    def start(self):
        self.__started = True
        # Set session close attributes to bars.
        for symbol, bars in self.__bars.iteritems():
            helpers.set_session_close_attributes(bars)
            self.__bars_left = max(self.__bars_left, len(bars))

    def stop(self):
        pass

    def join(self):
        pass

    def __iter__(self):
        return self

    def next(self):
        if self.stop_dispatching():
            self.__started = False
            raise StopIteration()
        return self.get_next_bars()

    def get_bars_left(self):
        return self.__bars_left

    # Dispatch events.
    def dispatch(self):
        bars = self.get_next_bars()
        if bars != None:
            for symbol in bars.get_symbols():
                self.__ds[symbol].append_value(bars.get_bar(symbol))
            self.__new_bars_event.emit(bars)

    def stop_dispatching(self):
        if self.__bars_left == 0:
            return True
        return False

    def get_bars(self, bars_ago=0):
        # this function will always be called *after* get_next_bars (which
        # increments self.__next_bar_idx) so we need to adjust bars_ago by +1
        # get_previous_bars(bars_ago=0) will therefore return the current bars.
        if self.__started:
            ret = self.__fetch_bars(bars_ago+1)
            return bar.Bars(ret) if ret else None
        raise Exception("Feed must be started before calling get_bars()")

    def get_next_bars(self):
        """Returns the next :class:`pytradelab.bar.Bars` in the feed or None if
        there are no bars."""
        if not self.__started:
            raise Exception("Feed must be started before calling get_bars()")
        bar_dict = self.fetch_next_bars()
        if bar_dict == None:
            return None

        # This will check for incosistent datetimes between bars.
        ret = bar.Bars(bar_dict)
        # Check that current bar datetimes are greater than the previous one.
        if self.__prev_date_time != None and self.__prev_date_time >= ret.get_date_time():
            raise Exception("Bar data times are not in order. Previous datetime was"\
                "%s and current datetime is %s" % (
                    self.__prev_date_time, ret.get_date_time()))
        self.__prev_date_time = ret.get_date_time()
        return ret

    def fetch_next_bars(self):
        ret = self.__fetch_bars()
        if ret:
            for symbol in ret:
                self.__next_bar_idx[symbol] += 1
            self.__bars_left -= 1
        return ret
        
    def __fetch_bars(self, bars_ago=0):
        # All bars must have the same datetime. We will return all the ones with the oldest datetime.
        # Make a first pass to get the oldest datetime.
        oldest_date_time = None
        for symbol, bars in self.__bars.iteritems():
            idx = self.__next_bar_idx[symbol] - bars_ago
            if idx >= 0 and idx < len(bars):
                if oldest_date_time == None or bars[idx].get_date_time() < oldest_date_time:
                    oldest_date_time = bars[idx].get_date_time()

        if oldest_date_time == None:
            assert(self.__bars_left == 0)
            return None

        # Make a second pass to get all the bars that had the oldest datetime.
        ret = {}
        for symbol, bars in self.__bars.iteritems():
            idx = self.__next_bar_idx[symbol] - bars_ago
            if idx >= 0 and idx < len(bars) and bars[idx].get_date_time() == oldest_date_time:
                ret[symbol] = bars[idx]
        return ret
