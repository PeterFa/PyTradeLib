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


class Database(object):
    def add_bars(self, bars, frequency):
        for symbol in bars.get_symbols():
            bar = bars.get_bar(symbol)
            self.add_bar(symbol, bar, frequency)

    def add_barsFromFeed(self, feed):
        feed.start()
        try:
            for bars in feed:
                if bars:
                    self.add_bars(bars, feed.get_frequency())
        finally:
            feed.stop()
            feed.join()

    def add_bar(self, symbol, bar, frequency):
        raise NotImplementedError()

    def get_bars(self, symbol, frequency, timezone=None, from_dateTime=None, to_date_time=None):
        raise NotImplementedError()
