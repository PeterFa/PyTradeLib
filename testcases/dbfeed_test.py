# PyAlgoTrade
# 
# Copyright 2012 Gabriel Martin Becedillas Ruiz
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
import os

from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import sqlitefeed
from pyalgotrade import barfeed
from pyalgotrade import marketsession
import common

class TemporarySQLiteFeed:
    def __init__(self, db_file_path, frequency):
        if os.path.exists(db_file_path):
            raise Exception("File exists")

        self.__db_file_path = db_file_path
        self.__frequency = frequency
        self.__feed = None

    def __enter__(self):
        self.__feed = sqlitefeed.Feed(self.__db_file_path, self.__frequency)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__feed = None
        os.remove(self.__db_file_path)

    def get_feed(self):
        return self.__feed

class SQLiteFeedTestCase(unittest.TestCase):
    dbName = "SQLiteFeedTestCase.sqlite"

    def testLoadDailyBars(self):
        tmpFeed = TemporarySQLiteFeed(SQLiteFeedTestCase.dbName, barfeed.Frequency.DAY)
        with tmpFeed:
            # Load bars using a Yahoo! feed.
            yahooFeed = yahoofeed.Feed()
            yahooFeed.add_bars_from_csv("orcl", common.get_data_file_path("orcl-2000-yahoofinance.csv"), marketsession.USEquities.timezone)
            yahooFeed.add_bars_from_csv("orcl", common.get_data_file_path("orcl-2001-yahoofinance.csv"), marketsession.USEquities.timezone)

            # Fill the database using the bars from the Yahoo! feed.
            sqliteFeed = tmpFeed.get_feed()
            sqliteFeed.get_database().add_barsFromFeed(yahooFeed)

            # Load the SQLite feed and process all bars.
            sqliteFeed.load_bars("orcl")
            sqliteFeed.start()
            for bars in sqliteFeed:
                pass
            sqliteFeed.stop()
            sqliteFeed.join()

            # Check that both dataseries have the same bars.
            yahooDS = yahooFeed["orcl"]
            sqliteDS = sqliteFeed["orcl"]
            self.assertEqual(len(yahooDS), len(sqliteDS))
            for i in xrange(len(yahooDS)):
                self.assertEqual(yahooDS[i].get_date_time(), sqliteDS[i].get_date_time())
                self.assertEqual(yahooDS[i].get_open(), sqliteDS[i].get_open())
                self.assertEqual(yahooDS[i].get_high(), sqliteDS[i].get_high())
                self.assertEqual(yahooDS[i].get_low(), sqliteDS[i].get_low())
                self.assertEqual(yahooDS[i].get_close(), sqliteDS[i].get_close())
                self.assertEqual(yahooDS[i].get_adj_close(), sqliteDS[i].get_adj_close())
                self.assertEqual(yahooDS[i].get_bars_until_session_close(), sqliteDS[i].get_bars_until_session_close())
                self.assertEqual(yahooDS[i].get_session_close(), sqliteDS[i].get_session_close())

def getTestCases():
    ret = []

    ret.append(SQLiteFeedTestCase("testLoadDailyBars"))

    return ret

