# This file is part of PyTradeLab.
#
# Copyright 2013 Brian A Cappello <briancappello at gmail>
#
# PyTradeLab is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyTradeLab is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyTradeLab.  If not, see http://www.gnu.org/licenses/

import os
import sys
import time
import logging
import datetime

from daemon.runner import DaemonRunner
from collections import defaultdict

from pytradelab import db
from pytradelab import utils
from pytradelab import settings
from pytradelab import historicalmanager
from pytradelab.failed import Symbols as FailedSymbols
from pytradelab.dataproviders.yahoo import yql

class TradingWeek:
    MarketOpen = datetime.time(9, 29) # hopefully our system clock's time is within a minute of Yahoo's.....
    MarketClose = datetime.time(16, 5) # accomodate any possible lag in EOD updates
    MarketCloseHistorical = datetime.time(20, 15) # Yahoo doesn't seem to update their EOD data until ~8PM EST

    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6

    Weekday = [0, 1, 2, 3, 4]
    Weekend = [5, 6]
    
    def market_open(self, date_time_now):
        if date_time_now.weekday() in self.Weekday:
            if self.MarketOpen < date_time_now.time() \
              and date_time_now.time() < self.MarketClose:
                return True
        return False

TradingWeek = TradingWeek()


class Manager(object):
    def __init__(self):
        self._db = db.Database()
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/var/run/testdaemon/testdaemon.pid'
        self.pidfile_timeout = 5
        self.__historical_manager = historicalmanager.DataManager()

        self.__update_intervals = {
            'symbol_index': {'days': [TradingWeek.Monday], 'time': TradingWeek.MarketOpen},
            'key_stats': {'days': TradingWeek.Weekday, 'time': TradingWeek.MarketClose},
            'intraday': {'days': TradingWeek.Weekday, 'timedelta': datetime.timedelta(seconds=25)},
            'historical': {'days': TradingWeek.Weekday, 'time': TradingWeek.MarketCloseHistorical},
            }

        self.__historical_initialized_handler = \
            self.__historical_manager.get_symbol_initialized_handler()
        self.__historical_updated_handler = \
            self.__historical_manager.get_symbol_updated_handler()

        self.__historical_initialized_handler.subscribe(self.__historical_initialized)
        self.__historical_updated_handler.subscribe(self.__historical_updated)

        if os.path.exists(settings.DATA_LAST_UPDATED_PATH):
            self.__last_updated = utils.load_from_json(settings.DATA_LAST_UPDATED_PATH)
        else:
            self.__last_updated = {
                'symbol_index': {},
                'historical_initialized': defaultdict(dict),
                'historical': defaultdict(dict),
                'key_stats': {},
                }

    def run(self):
        while True:
            logger.debug('Debug Message')
            logger.info('Info Message')
            logger.warn('Warning')
            logger.error('Error')

            logger.info('sleeping for 10 seconds')
            time.sleep(10)

    def index_updated(self):
        return self._db.index_updated()

    def update_index(self):
        if not self.index_updated():
            self._update_index(index)

    def _update_index(self, index):
        new_index = yql.SymbolIndex.get_data()
        all_new_symbols = [x['symbol'] for x in new_index['symbols']]
        all_existing_symbols = self._db.get_symbols()
        new_symbols = \
            [x for x in all_new_symbols if x not in all_existing_symbols]
        removed_symbols = \
            [x for x in all_existing_symbols if x not in all_new_symbols]
        for symbol in removed_symbols:
            self._db.delete_symbol(symbol)
        self.__init_or_update_index(new_index)

        # FIXME: emit these changes instead of printing them
        if new_symbols:
            print 'newly added symbols: %s\n' % new_symbols
        else:
            print 'no new symbols in this index update'

        if removed_symbols:
            print 'removed symbols: %s\n' % removed_symbols
        else:
            print 'no removed symbols in this index update'

    def __init_or_update_index(self, index):
        self._db.insert_or_update_sectors(index['sectors'])
        self._db.insert_or_update_industries(index['industry_sectors'])
        self._db.insert_or_update_symbols(index['symbols'])

    def historical_initialized(self, symbol, frequency):
        return self.__last_updated['historical_initialized'][symbol].get(frequency, False)

    def historical_updated(self, symbol, frequency):
        return self.__last_updated['historical_updated'][symbol].get(frequency, False)

    def __historical_initialized(self, symbol, frequency):
        self.__last_updated['historical_initialized'][symbol][frequency] = True

    def __historical_updated(self, symbol, frequency):
        self.__last_updated['historical_updated'][symbol][frequency] = True

    def key_stats_updated(self, symbol):
        return self.__last_updated['key_stats_updated'].get(symbol, False)

    def __key_stats_updated(self, symbol):
        self.__last_updated['key_stats_updated'][symbol] = True

if __name__ == '__main__':
    um = Manager()
    logger = logging.getLogger('SymbolUpdateManager')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler('/var/log/testdaemon/testdaemon.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    runner = DaemonRunner(um)
    runner.daemon_context.files_preserve=[handler.stream]
    runner.do_action()
    