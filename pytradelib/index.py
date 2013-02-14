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

from pytradelib import utils
from pytradelib import settings
from pytradelib import historicalmanager
from pytradelib import updatemanager
from pytradelib import containers


class Factory(object):
    def __init__(self):
        self.__historical_manager = historicalmanager.DataManager()
        self.__update_manager = updatemanager.Manager()
        self.__index = self.__load_index()
        self.__instruments = {}
        self.__sectors = {}
        self.__industries = {}

    def __load_index(self):
        if not self.__update_manager.index_initialized():
            self.__update_manager.update_index()
        # FIXME: figure out a better design than using UM's internal _db variable
        index = self.__update_manager._db.get_index()
        index['symbols'] = dict((x['symbol'], x) for x in index['symbols'])
        index['industry_sectors'] = dict((x, y) for x, y in index['industry_sectors'])
        index['sector_industries'] = dict((x, []) for x in index['sectors'])
        for industry, sector in index['industry_sectors'].items():
            index['sector_industries'][sector].append(industry)
        return index

    def set_bar_filter(self, bar_filter):
        self.__historical_manager.set_bar_filter(bar_filter)

    def symbols(self):
        return sorted(self.__index['symbols'].keys())

    def sectors(self):
        return sorted(self.__index['sectors'])

    def industries(self):
        return sorted(self.__index['industry_sectors'].keys())

    @utils.lower
    def get_instrument(self, symbol):
        if symbol not in self.__instruments:
            self.__instruments[symbol] = containers.Instrument(symbol,
                self.__index['symbols'][symbol]['name'],
                self.__index['symbols'][symbol]['sector'],
                self.__index['symbols'][symbol]['industry'],
                self.__historical_manager)
        return self.__instruments[symbol]

    def get_instruments(self, symbols=None):
        symbols = symbols or self.__index['symbols'].keys()
        ret = []
        for symbol in symbols:
            ret.append(self.get_instrument(symbol))
        return ret

    def get_watch_list(self, list_name, symbols=None):
        symbols = symbols or self.__index['symbols'].keys()
        watch_list = containers.WatchList(list_name)
        for symbol in symbols:
            watch_list.add_instrument(self.get_instrument(symbol))
        return watch_list

    def get_industry(self, name):
        if name not in self.__industries:
            self.__industries[name] = containers.Industry(name, self.__index['industry_sectors'][name])
            for symbol in self.__index['industry_symbols'][name]:
                self.__industries[name].add_instrument(self.get_instrument(symbol))
        return self.__industries[name]

    def get_sector(self, name):
        if name not in self.__sectors:
            sector = containers.Sector(name)
            for industry_name in self.__index['sector_industries'][name]:
                sector.add_industry(self.get_industry(industry_name))
            sector.set_instruments()
            self.__sectors[name] = sector
        return self.__sectors[name]
