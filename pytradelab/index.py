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

from pytradelab import utils
from pytradelab import settings
from pytradelab import historicalmanager
from pytradelab import updatemanager
from pytradelab import containers


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
        return utils.load_from_json(settings.SYMBOL_INDEX_PATH)

    def set_bar_filter(self, bar_filter):
        self.__historical_manager.set_bar_filter(bar_filter)

    def symbols(self):
        return sorted(self.__index['all_symbols'].keys())

    def sectors(self):
        return sorted(self.__index['sector_industries'].keys())

    def industries(self):
        return sorted(self.__index['industry_symbols'].keys())

    @utils.lower
    def get_instrument(self, symbol):
        if symbol not in self.__instruments:
            self.__instruments[symbol] = containers.Instrument(symbol,
                self.__index['all_symbols'][symbol]['name'],
                self.__index['all_symbols'][symbol]['sector'],
                self.__index['all_symbols'][symbol]['industry'],
                self.__historical_manager)
        return self.__instruments[symbol]

    def get_instruments(self, symbols=None):
        symbols = symbols or self.__index['all_symbols'].keys()
        ret = []
        for symbol in symbols:
            ret.append(self.get_instrument(symbol))
        return ret

    def get_watch_list(self, list_name, symbols=None):
        symbols = symbols or self.__index['all_symbols'].keys()
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


#def load_symbol_index(update=None):
    #'''
    #Loads the symbol index from disk. If update is not specified, the default
    #behavior is to update if existing data is older than the timedelta specified
    #in settings.
    #'''
    #if update == None:
        #update = True
        #if __key_updated('symbol_index'):
            #update = False
    #if update or not os.path.exists(settings.SYMBOL_INDEX_PATH):
        #changes = update_symbol_index()
        #print 'added symbols: %s\n' % changes['new_symbols']
        #print 'removed symbols: %s\n' % changes['removed_symbols']
    #return utils.load_from_json(settings.SYMBOL_INDEX_PATH)

#def update_symbol_index():
    ## FIXME: this function is huge. it's crap.
    #'''
    #Updates the symbol index with new data. Returns a dict with two keys
    #'new' and 'removed' whose values are dicts of symbols.
    #'''
    #initial_download = False
    #if not os.path.exists(settings.SYMBOL_INDEX_PATH):
        #initial_download = True

    ## get all yahoo industry IDs so we can get all the symbols for each industry
    #sector_industries = yql.get_sectors_and_industries(download=True)
    #industry_sectors = {}
    #yahoo_ids = []
    #for sector, industries in sector_industries.items():
        #if not isinstance(industries, list):
            #industries = [industries]
        #for industry in industries:
            #yahoo_ids.append(industry['id'])
            #industry_sectors[industry['name']] = sector

    ## create a nested dict with all the symbols available from yahoo
    #symbols = {}
    #industries = {}
    #json_industries = yql.industries._download(yahoo_ids)
    #for json_industry in json_industries:
        #industry_name = json_industry['name']
        #industry_symbols = []
        #if 'company' in json_industry.keys():
            #for json_instrument in json_industry['company']:
                #if isinstance(json_instrument, dict):
                    #symbol = json_instrument['symbol'].lower()
                    #symbols[symbol] = {
                        #'symbol': symbol,
                        #'sector': industry_sectors[industry_name],
                        #'industry': industry_name,
                        #'name': json_instrument['name'].encode('utf-8'),
                        #}
                    #industry_symbols.append(symbol)
        #industries[industry_name] = industry_symbols

    ## compare the new data against the original data and save the differences
    #if initial_download:
        #new = symbols
        #removed = {}
    #else:
        #original = load_symbol_index(update=False)['all_symbols']
        #new = {}
        #for symbol in symbols:
            #if symbol not in original:
                #new[symbol] = symbols[symbol]
            #else:
                #original.pop(symbol)
        #removed = original

    #ret = {
        #'new_symbols': new,
        #'removed_symbols': removed,
        #'all_symbols': symbols,
        #'sector_industries': sector_industries,
        #'industry_symbols': industries,
        #'industry_sectors': industry_sectors,
        #}
    #utils.save_to_json(ret, settings.SYMBOL_INDEX_PATH)
    ## FIXME
    ##__set_updated_time('symbol_index', datetime.datetime.now()) # FIXME: UTC
    #return ret
    
