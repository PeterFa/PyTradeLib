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

from pytradelab import barfeed
from pytradelab.barfeed import helpers

# This class is responsible for:
# - Holding bars in memory.
# - Aligning them with respect to time.
#
# Subclasses should:
# - Forward the call to start() if they override it.

class Feed(barfeed.BarFeed):
    def __init__(self, frequency):
        barfeed.BarFeed.__init__(self, frequency)
        self.__bars = {}
        self.__next_bar_idx = {}
        self.__started = False
        self.__bars_left = 0

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

    def add_bars_from_sequence(self, symbol, bars):
        if self.__started:
            raise Exception("Can't add more bars once you started consuming bars")

        self.__bars.setdefault(symbol, [])
        self.__next_bar_idx.setdefault(symbol, 0)

        # Add and sort the bars
        self.__bars[symbol].extend(bars)
        barCmp = lambda x, y: cmp(x.get_date_time(), y.get_date_time())
        self.__bars[symbol].sort(barCmp)

        self.register_symbol(symbol)

    def stop_dispatching(self):
        ret = True
        # Check if there is at least one more bar to return.
        for symbol, bars in self.__bars.iteritems():
            next_idx = self.__next_bar_idx[symbol]
            if next_idx < len(bars):
                ret = False
                break
        return ret

    def fetch_next_bars(self):
        # All bars must have the same datetime. We will return all the ones with the smallest datetime.
        oldest_date_time = None

        # Make a first pass to get the smallest datetime.
        for symbol, bars in self.__bars.iteritems():
            next_idx = self.__next_bar_idx[symbol]
            if next_idx < len(bars):
                if oldest_date_time == None or bars[next_idx].get_date_time() < oldest_date_time:
                    oldest_date_time = bars[next_idx].get_date_time()

        if oldest_date_time == None:
            assert(self.__bars_left == 0)
            return None

        # Make a second pass to get all the bars that had the smallest datetime.
        ret = {}
        for symbol, bars in self.__bars.iteritems():
            next_idx = self.__next_bar_idx[symbol]
            if next_idx < len(bars) and bars[next_idx].get_date_time() == oldest_date_time:
                ret[symbol] = bars[next_idx]
                self.__next_bar_idx[symbol] += 1

        self.__bars_left -= 1
        return ret

    def get_bars_left(self):
        return self.__bars_left

