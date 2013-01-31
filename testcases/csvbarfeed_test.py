# PyAlgoTrade
# 
# Copyright 2011 Gabriel Martin Becedillas Ruiz
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#	http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import unittest
import datetime

from pyalgotrade.barfeed import csvfeed
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import ninjatraderfeed
from pyalgotrade.utils import dt
from pyalgotrade import marketsession
import common

class BarFeedEventHandler_TestLoadOrder:
    def __init__(self, testcase, bar_feed, symbol):
        self.__testcase = testcase
        self.__count = 0
        self.__prev_date_time = None
        self.__bar_feed = bar_feed
        self.__symbol = symbol

    def on_bars(self, bars):
        self.__count += 1
        date_time = bars.get_bar(self.__symbol).get_date_time()
        if self.__prev_date_time != None:
            # Check that bars are loaded in order
            self.__testcase.assertTrue(self.__prev_date_time < date_time)
            # Check that the last value in the dataseries match the current datetime.
            self.__testcase.assertTrue(self.__bar_feed.get_data_series().get_value().get_date_time() == date_time)
        self.__prev_date_time = date_time

    def get_eventCount(self):
            return self.__count
    
class BarFeedEventHandler_TestFilterRange:
    def __init__(self, testcase, symbol, from_date, toDate):
        self.__testcase = testcase
        self.__count = 0
        self.__symbol = symbol
        self.__from_date = from_date
        self.__toDate = toDate

    def on_bars(self, bars):
        self.__count += 1

        if self.__from_date != None:
            self.__testcase.assertTrue(bars.get_bar(self.__symbol).get_date_time() >= self.__from_date)
        if self.__toDate != None:
            self.__testcase.assertTrue(bars.get_bar(self.__symbol).get_date_time() <= self.__toDate)

    def get_eventCount(self):
            return self.__count

class YahooTestCase(unittest.TestCase):
    TestInstrument = "orcl"

    def __parse_date(self, date):
        parser = csvfeed.YahooRowParser(datetime.time(23, 59))
        row = {"Date":date, "Close":0, "Open":0 , "High":0 , "Low":0 , "Volume":0 , "Adj Close":0}
        return parser.parse_bar(row).get_date_time()

    def testParseDate_1(self):
        date = self.__parse_date("1950-1-1")
        self.assertTrue(date.day == 1)
        self.assertTrue(date.month == 1)
        self.assertTrue(date.year == 1950)

    def testParseDate_2(self):
        date = self.__parse_date("2000-1-1")
        self.assertTrue(date.day == 1)
        self.assertTrue(date.month == 1)
        self.assertTrue(date.year == 2000)

    def testDateCompare(self):
        self.assertTrue(self.__parse_date("2000-1-1") == self.__parse_date("2000-1-1"))
        self.assertTrue(self.__parse_date("2000-1-1") != self.__parse_date("2001-1-1"))
        self.assertTrue(self.__parse_date("1999-1-1") < self.__parse_date("2001-1-1"))
        self.assertTrue(self.__parse_date("2011-1-1") > self.__parse_date("2001-2-2"))

    def testCSVFeedLoadOrder(self):
        bar_feed = csvfeed.YahooFeed()
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"))
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))

        # Dispatch and handle events.
        handler = BarFeedEventHandler_TestLoadOrder(self, bar_feed, YahooTestCase.TestInstrument)
        bar_feed.get_new_bars_event().subscribe(handler.on_bars)
        while not bar_feed.stop_dispatching():
            bar_feed.dispatch()
        self.assertTrue(handler.get_eventCount() > 0)

    def __testFilteredRangeImpl(self, from_date, toDate):
        bar_feed = csvfeed.YahooFeed()
        bar_feed.set_bar_filter(csvfeed.DateRangeFilter(from_date, toDate))
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"))
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))

        # Dispatch and handle events.
        handler = BarFeedEventHandler_TestFilterRange(self, YahooTestCase.TestInstrument, from_date, toDate)
        bar_feed.get_new_bars_event().subscribe(handler.on_bars)
        while not bar_feed.stop_dispatching():
            bar_feed.dispatch()
        self.assertTrue(handler.get_eventCount() > 0)

    def testFilteredRangeFrom(self):
        # Only load bars from year 2001.
        self.__testFilteredRangeImpl(datetime.datetime(2001, 1, 1, 00, 00), None)

    def testFilteredRangeTo(self):
        # Only load bars up to year 2000.
        self.__testFilteredRangeImpl(None, datetime.datetime(2000, 12, 31, 23, 55))

    def testFilteredRangeFromTo(self):
        # Only load bars in year 2000.
        self.__testFilteredRangeImpl(datetime.datetime(2000, 1, 1, 00, 00), datetime.datetime(2000, 12, 31, 23, 55))

    def testWithoutTimezone(self):
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"))
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        bar_feed.start()
        for bars in bar_feed:
            bar = bars.get_bar(YahooTestCase.TestInstrument)
            self.assertTrue(dt.datetime_is_naive(bar.get_date_time()))
        bar_feed.stop()
        bar_feed.join()

    def testWithDefaultTimezone(self):
        bar_feed = yahoofeed.Feed(marketsession.USEquities.getTimezone())
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"))
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"))
        bar_feed.start()
        for bars in bar_feed:
            bar = bars.get_bar(YahooTestCase.TestInstrument)
            self.assertFalse(dt.datetime_is_naive(bar.get_date_time()))
        bar_feed.stop()
        bar_feed.join()

    def testWithPerFileTimezone(self):
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"), marketsession.USEquities.getTimezone())
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2001-yahoofinance.csv"), marketsession.USEquities.getTimezone())
        bar_feed.start()
        for bars in bar_feed:
            bar = bars.get_bar(YahooTestCase.TestInstrument)
            self.assertFalse(dt.datetime_is_naive(bar.get_date_time()))
        bar_feed.stop()
        bar_feed.join()

    def testWithIntegerTimezone(self):
        try:
            bar_feed = yahoofeed.Feed(-5)
            self.assertTrue(False, "Exception expected")
        except Exception, e:
            self.assertTrue(str(e).find("timezone as an int parameter is not supported anymore") == 0)

        try:
            bar_feed = yahoofeed.Feed()
            bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"), -3)
            self.assertTrue(False, "Exception expected")
        except Exception, e:
            self.assertTrue(str(e).find("timezone as an int parameter is not supported anymore") == 0)

    def testMapTypeOperations(self):
        bar_feed = yahoofeed.Feed()
        bar_feed.add_bars_from_csv(YahooTestCase.TestInstrument, common.get_data_file_path("orcl-2000-yahoofinance.csv"), marketsession.USEquities.getTimezone())
        bar_feed.start()
        for bars in bar_feed:
            self.assertTrue(YahooTestCase.TestInstrument in bars)
            self.assertFalse(YahooTestCase.TestInstrument not in bars)
            bars[YahooTestCase.TestInstrument]
            with self.assertRaises(KeyError):
                bars["pirulo"]
        bar_feed.stop()
        bar_feed.join()

class NinjaTraderTestCase(unittest.TestCase):
    def __loadIntradayBarFeed(self, timeZone = None):
        ret = ninjatraderfeed.Feed(ninjatraderfeed.Frequency.MINUTE, timeZone)
        ret.add_bars_from_csv("spy", common.get_data_file_path("nt-spy-minute-2011.csv"))
        # This is need to get session close attributes set. Strategy class is responsible for calling this.
        ret.start()
        # Process all events to get the dataseries fully loaded.
        while not ret.stop_dispatching():
            ret.dispatch()
        ret.stop()
        ret.join()
        return ret

    def testWithTimezone(self):
        timeZone = marketsession.USEquities.getTimezone()
        bar_feed = self.__loadIntradayBarFeed(timeZone)
        ds = bar_feed.get_data_series()

        for i in xrange(ds.get_length()):
            current_bar = ds[i]
            self.assertFalse(dt.datetime_is_naive(current_bar.get_date_time()))

    def testWithoutTimezone(self):
        bar_feed = self.__loadIntradayBarFeed(None)
        ds = bar_feed.get_data_series()

        for i in xrange(ds.get_length()):
            current_bar = ds[i]
            # Datetime must be set to UTC.
            self.assertFalse(dt.datetime_is_naive(current_bar.get_date_time()))

    def testWithIntegerTimezone(self):
        try:
            bar_feed = ninjatraderfeed.Feed(ninjatraderfeed.Frequency.MINUTE, -3)
            self.assertTrue(False, "Exception expected")
        except Exception, e:
            self.assertTrue(str(e).find("timezone as an int parameter is not supported anymore") == 0)

        try:
            bar_feed = ninjatraderfeed.Feed(ninjatraderfeed.Frequency.MINUTE)
            bar_feed.add_bars_from_csv("spy", common.get_data_file_path("nt-spy-minute-2011.csv"), -5)
            self.assertTrue(False, "Exception expected")
        except Exception, e:
            self.assertTrue(str(e).find("timezone as an int parameter is not supported anymore") == 0)

    def testLocalizeAndFilter(self):
        timezone = marketsession.USEquities.getTimezone()
        # The prices come from NinjaTrader interface when set to use 'US Equities RTH' session template.
        prices = {
            dt.localize(datetime.datetime(2011, 3, 9, 9, 31), timezone) : 132.35,
            dt.localize(datetime.datetime(2011, 3, 9, 16), timezone) : 132.39,
            dt.localize(datetime.datetime(2011, 3, 10, 9, 31), timezone) : 130.81,
            dt.localize(datetime.datetime(2011, 3, 10, 16), timezone) : 129.92,
            dt.localize(datetime.datetime(2011, 3, 11, 9, 31), timezone) : 129.72,
            dt.localize(datetime.datetime(2011, 3, 11, 16), timezone) : 130.84,
        }
        bar_feed = ninjatraderfeed.Feed(ninjatraderfeed.Frequency.MINUTE, timezone)
        bar_feed.add_bars_from_csv("spy", common.get_data_file_path("nt-spy-minute-2011-03.csv"))
        for bars in bar_feed:
            price = prices.get(bars.get_date_time(), None)
            if price != None:
                self.assertTrue(price == bars.get_bar("spy").get_close())

def getTestCases():
    ret = []

    ret.append(YahooTestCase("testParseDate_1"))
    ret.append(YahooTestCase("testParseDate_2"))
    ret.append(YahooTestCase("testDateCompare"))
    ret.append(YahooTestCase("testCSVFeedLoadOrder"))
    ret.append(YahooTestCase("testFilteredRangeFrom"))
    ret.append(YahooTestCase("testFilteredRangeTo"))
    ret.append(YahooTestCase("testFilteredRangeFromTo"))
    ret.append(YahooTestCase("testWithoutTimezone"))
    ret.append(YahooTestCase("testWithDefaultTimezone"))
    ret.append(YahooTestCase("testWithPerFileTimezone"))
    ret.append(YahooTestCase("testWithIntegerTimezone"))
    ret.append(YahooTestCase("testMapTypeOperations"))

    ret.append(NinjaTraderTestCase("testWithTimezone"))
    ret.append(NinjaTraderTestCase("testWithoutTimezone"))
    ret.append(NinjaTraderTestCase("testWithIntegerTimezone"))
    ret.append(NinjaTraderTestCase("testLocalizeAndFilter"))

    return ret


# vim: noet:ci:pi:sts=0:sw=4:ts=4
