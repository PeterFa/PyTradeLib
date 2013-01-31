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

import sys
sys.path.append("..")

from pyalgotrade.barfeed import sqlitefeed
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import marketsession
from pyalgotrade.tools import yahoofinance
import pyalgotrade.logger

import tempfile

logger = pyalgotrade.logger.get_logger("update-db")

def download_bars(db, symbol, year, timezone):
    try:
        # Download bars.
        csvFile = tempfile.NamedTemporaryFile()
        csvFile.write(yahoofinance.get_daily_csv(symbol, year))
        csvFile.flush()

        # Load them into a feed.
        feed = yahoofeed.Feed()
        feed.add_bars_from_csv(symbol, csvFile.name, timezone)

        # Put them in the db.
        db.add_barsFromFeed(feed)
    except Exception, e:
        logger.error("Error downloading %s bars for %s: %s" % (symbol, year, str(e)))

def update_bars(db_file_path, symbolsFile, timezone, from_year, to_year):
    db = sqlitefeed.Database(db_file_path)
    for symbol in open(symbolsFile, "r"):
        symbol = symbol.strip()
        logger.info("Downloading %s bars" % (symbol))
        for year in range(from_year, to_year+1):
            download_bars(db, symbol, year, timezone)

def main():
    from_year = 2000
    to_year = 2012
    update_bars("yahoofinance.sqlite", "nasdaq-symbols.txt", marketsession.NASDAQ.timezone, from_year, to_year)
    update_bars("yahoofinance.sqlite", "nyse-symbols.txt", marketsession.NYSE.timezone, from_year, to_year)

main()

