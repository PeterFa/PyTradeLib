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

from pytradelab.barfeed import csvfeed

import types

######################################################################
## Yahoo Finance CSV parser
# Each bar must be on its own line and fields must be separated by comma (,).
#
# Bars Format:
# Date,Open,High,Low,Close,Volume,Adj Close
#
# The csv Date column must have the following format: YYYY-MM-DD

class RowParser(csvfeed.YahooRowParser):
    pass

class Feed(csvfeed.YahooFeed):
    """A :class:`pytradelab.barfeed.csvfeed.BarFeed` that loads bars from CSV files downloaded from Yahoo! Finance.

    :param timezone: The default timezone to use to localize bars. Check :mod:`pytradelab.marketsession`.
    :type timezone: A pytz timezone.

    .. note::
        Yahoo! Finance csv files lack timezone information.
        When working with multiple symbols:

            * If all the symbols loaded are in the same timezone, then the timezone parameter may not be specified.
            * If any of the symbols loaded are from different timezones, then the timezone parameter must be set.
    """
    def __init__(self, timezone=None):
        csvfeed.YahooFeed.__init__(self, timezone, True)

    def add_bars_from_csv(self, symbol, path, timezone=None):
        """Loads bars for a given symbol from a CSV formatted file.
        The symbol gets registered in the bar feed.

        :param symbol: Instrument identifier.
        :type symbol: string.
        :param path: The path to the file.
        :type path: string.
        :param timezone: The timezone to use to localize bars. Check :mod:`pytradelab.marketsession`.
        :type timezone: A pytz timezone.
        """
        csvfeed.YahooFeed.add_bars_from_csv(self, symbol, path, timezone)
