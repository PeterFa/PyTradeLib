# This file is part of PyTradeLib.
#
# Copyright 2013 Brian A Cappello <briancappello at gmail>
#
# PyTradeLib is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyTradeLib is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyTradeLib.  If not, see http://www.gnu.org/licenses/

import os
import sys
import time
import logging
import datetime

from daemon.runner import DaemonRunner

from pytradelib import db as db_
from pytradelib import bar
from pytradelib import historicalmanager
from pytradelib.failed import Symbols as FailedSymbols
from pytradelib.dataproviders.yahoo import yql


class Month(object):
    Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec = range(1, 13)

    def get_days(self, month, year):
        if month == self.Feb:
            try:
                return datetime.date(year, month, 29).day
            except ValueError:
                return 28
        elif month in [self.Apr, self.Jun, self.Sep, self.Nov]:
            return 30
        else:
            return 31

Month = Month()


class TradingWeek(object):
    MarketOpen = datetime.time(9, 29) # hopefully our system clock's time is within a minute of Yahoo's.....
    MarketClose = datetime.time(16, 5) # accomodate any possible lag in EOD updates
    MarketCloseHistorical = datetime.time(20, 15) # Yahoo doesn't seem to update their EOD data until ~8PM EST

    Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday = range(0, 7)
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
    def __init__(self, db=None):
        self._db = db or db_.Database()
        self.__update_intervals = {
            'symbol_index': {'days': [TradingWeek.Monday], 'time': TradingWeek.MarketOpen},
            'key_stats': {'days': TradingWeek.Weekday, 'time': TradingWeek.MarketClose},
            'intraday': {'days': TradingWeek.Weekday, 'timedelta': datetime.timedelta(seconds=25)},
            'historical': {'days': TradingWeek.Weekday, 'time': TradingWeek.MarketCloseHistorical},
            }

        # initialize our data managers and subscribe to update events
        self._historical_reader = historicalmanager.DataReader()
        self._historical_updater = historicalmanager.DataUpdater(self._db)
        self.__historical_updated_handler = \
            self._historical_updater.get_symbol_updated_handler()
        self.__historical_updated_handler.subscribe(
            self.__historical_updated_event)

        # setup for running as a daemon
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/var/run/testdaemon/testdaemon.pid'
        self.pidfile_timeout = 5

    @property
    def historical_reader(self):
        return self._historical_reader

    def run(self):
        while True:
            logger.debug('Debug Message')
            logger.info('Info Message')
            logger.warn('Warning')
            logger.error('Error')
            logger.info('sleeping for 10 seconds')
            time.sleep(10)

    def index_initialized(self):
        return True if self._db.get_updated('symbol_index') else False

    def index_updated(self):
        last_updated = self._db.get_updated('symbol_index')
        if not last_updated:
            return False
        update_day = self.__update_intervals['symbol_index']['days'][0]
        update_time = self.__update_intervals['symbol_index']['time']
        update_date = datetime.datetime.today()
        while(update_date.weekday() > update_day): # this relies on update_day = 0
            day = update_date.day - 1
            month = update_date.month
            year = update_date.year
            if day < 1:
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                day = Month.get_days(month, year)
            update_date = datetime.date(year, month, day)
            if update_date.weekday() == update_day:
                break
        update_date_time = datetime.datetime.combine(update_date, update_time)
        if last_updated < update_date_time:
            return False
        return True

    def update_index(self):
        if not self.index_updated():
            self._update_index()

    def _update_index(self):
        new_index = yql.SymbolIndex.get_data()
        self._db.set_updated('symbol_index')
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

    def _initialize_historical(self, symbols, frequency=None):
        self._historical_updater.initialize_symbols(symbols, frequency)

    def _update_historical(self, symbols, frequency=None):
        self._historical_updater.update_symbols(symbols, frequency)

    def __init_or_update_index(self, index):
        self._db.insert_or_update_sectors(index['sectors'])
        self._db.insert_or_update_industries(index['industry_sectors'])
        self._db.insert_or_update_symbols(index['symbols'])

    def __historical_updated_event(self, symbol, frequency):
        bar_ = self._historical_reader.get_newest_bar(symbol, frequency)
        self._db.set_updated(
            bar.FrequencyToStr[frequency], symbol, bar_.get_date_time())

    #def key_stats_updated(self, symbol):
        #return self.__last_updated['key_stats_updated'].get(symbol, False)

    #def __key_stats_updated(self, symbol):
        #self.__last_updated['key_stats_updated'][symbol] = True

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
    