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
import datetime

from pytradelib import utils
from pytradelib import settings
from pytradelib.dataproviders.yahoo import yql

from pytradelib import bar
from pytradelib import dataseries


class Instrument(object):
    @utils.lower
    def __init__(self, symbol, name, sector, industry, historical_reader):
        self.__symbol = symbol
        self.__name = name
        self.__sector = sector
        self.__industry = industry
        self.__historical_reader = historical_reader

        self.__dict = {
            'Symbol': symbol,
            'Name': name,
            'Industry': industry,
            'Sector': sector,
            }
        self.__bar_ds = None

    def data_folder(self):
        # FIXME: pull from __historical_reader
        return os.path.join(settings.DATA_DIR, 'symbols', self.symbol())

    def set_bar_filter(self, bar_filter):
        self.__historical_reader.set_bar_filter(bar_filter)

    def symbol(self):
        return self.__symbol

    def name(self):
        return self.__name

    def sector(self):
        return self.__sector

    def industry(self):
        return self.__industry

    #def get_quote(self):
        #if not self.quote_updated():
            #self.update_quote()

        #ret = self.get_values([
            #'LastTradeDateTime',
            #'Open',
            #'DaysHigh',
            #'DaysLow',
            #'LastTradePriceOnly',
            #'Volume',
            #])
        #return ret

    #def get_quote_bar(self):
        #try:
            #bar_ = self.__quote_to_bar(self.__dict)
        #except TypeError, e:
            #bar_ = self.get_bar()
        #return bar_

    def get_recarray(self, frequency=None):
        return self.__historical_reader.get_recarray(self.__symbol, frequency)

    def get_bar(self, frequency=None, bars_ago=0):
        if bars_ago != 0:
            raise NotImplementedError() # FIXME
        bar_ = self.__historical_reader.get_newest_bar(self.__symbol, frequency)
        return bar_

    def get_bars(self, frequency=None, bar_filter=None):
        self.set_bar_filter(bar_filter)
        return self.__historical_reader.get_bars(self.__symbol, frequency)

    def get_data_series(self, frequency=None, bar_filter=None):
        self.set_bar_filter(bar_filter)
        if self.__bar_ds == None:
            self.__bar_ds = dataseries.BarDataSeries()
            for bar_ in self.get_bars():
                self.__bar_ds.appendValue(bar_)
        return self.__bar_ds

    def get_stats(self):
        #if not self.stats_updated():
            #self.update_stats()
        ret = self.get_values(yql.KeyStats.keys())
        ret.pop('ErrorIndicationreturnedforsymbolchangedinvalid')
        return ret

    def update_stats(self, stats=None):
        if stats == None: # and not self.stats_updated():
            stats = yql.KeyStats.get_data(self.symbol())
        if self.symbol() in stats:
            #UpdateManager.set_stats_updated(self.symbol())
            self.__dict.update(stats[self.symbol()])

    #def stats_updated(self):
        #return UpdateManager.stats_updated(self.symbol())

    def keys(self):
        return sorted(self.__dict.keys())

    def get_values(self, keys=None):
        keys = keys or self.__dict.keys()
        ret = {}
        for key in keys:
            ret[key] = self.__dict[key]
        return ret

    def __getitem__(self, key):
        return self.__dict.get(key, None)

    def __setitem__(self, key, value):
        if key not in yql.KeyStats.keys():
            self.__dict[key] = value
        else:
            print 'Failed to set read-only key "%s". Please use a key not reserved by Yahoo!.' % key

    #def __quote_to_bar(self, quote):
        #bar_ = bar.Bar(
            #quote['LastTradeDateTime'],
            #quote['Open'],
            #quote['DaysHigh'],
            #quote['DaysLow'],
            #quote['LastTradePriceOnly'],
            #quote['Volume'],
            #quote['LastTradePriceOnly'])
        #return bar_

    def __str__(self):
        return '%s (%s, %s - %s)' % (self.symbol(), self.name(),
            self.sector(), self.industry())


class Instruments(object):
    def __init__(self, name=None):
        self.__name = name
        self.__bar_filter = None
        self.__instruments = {}

    def name(self):
        return self.__name

    def slug(self):
        return utils.slug(self.name())

    def data_folder(self):
        return os.path.join(settings.DATA_DIR, 'watchlists', self.slug())

    def set_bar_filter(self, bar_filter):
        self.__bar_filter = bar_filter
        for instrument in self.__instruments:
            instrument.set_bar_filter(bar_filter)

    def symbols(self):
        return sorted(self.__instruments.keys())

    @utils.lower
    def get_instrument(self, symbol=None):
        if symbol == None:
            return self.__instruments.popitem()[1]
        return self.__instruments[symbol]

    def get_instruments(self, symbols=None):
        if symbols == None:
            return self.__instruments.values()
        ret = []
        for symbol in symbols:
            ret.append(self.get_instrument(symbol))
        return ret

    def set_instruments(self, instruments):
        for instrument in instruments:
            self.add_instrument(instrument)

    def add_instrument(self, instrument):
        if self.__bar_filter:
            instrument.set_bar_filter(self.__bar_filter)
        self.__instruments[instrument.symbol()] = instrument

    @utils.lower
    def remove_instrument(self, symbol):
        return self.__instruments.pop(symbol)

    def update_stats(self, instruments=None):
        instruments = instruments or self.__instruments.values()
        stats = yql.KeyStats.get_data([x.symbol() for x in instruments])
        for symbol_stats in stats:
            instrument = self.get_instrument(symbol_stats['symbol'])
            instrument.update_stats(symbol_stats)

    #def update_historical(self, instruments=None):


class Industry(Instruments):
    def __init__(self, name, sector=None):
        Instruments.__init__(self, name)
        self.__sector = sector

    def data_folder(self):
        return os.path.join(self.sector().data_folder(), self.slug())

    def sector(self):
        return self.__sector


class Sector(Instruments):
    def __init__(self, name):
        Instruments.__init__(self, name)
        self.__industries = {}

    def data_folder(self):
        return os.path.join(settings.DATA_DIR, 'sectors', self.slug())

    def industries(self):
        return sorted(self.__industries.keys())

    def get_industry(self, name):
        return self.__industries[name]

    def get_industries(self):
        return self.__industries

    def set_industries(self, industries):
        self.__industries = industries

    def add_industry(self, industry):
        self.__industries[industry.name()] = industry

    def set_instruments(self):
        for industry in self.get_industries():
            for instrument in industry.get_instruments():
                self.add_instrument(instrument)


#class SectorIndex(Instruments):
    #def __init__(self, download=False):
        #self.__sectors = None
        #self.__industries = None

        #self.update_sectors_and_industries(download)
        #self.update_industry_instruments(download)
        #self.update_instrument_quote_stats(download)

    #def data_folder(self):
        #return os.path.join(settings.DATA_DIR, 'sectors')

    #def sectors(self):
        #''' Returns a list all sector names.
        #'''
        #return sorted(self.get_sectors().keys())

    #def get_sector(self, name):
        #''' Returns the :class:`Sector` with the given name.
        #'''
        #return self.get_sectors()[name]

    #def get_sectors(self, sectors=None):
        #''' Returns a dict of all Sectors. {sector_name: :class:`Sector`}
        #'''
        #if self.__sectors == None:
            #self.update_sectors_and_industries()
        #if sectors == None:
            #return self.__sectors
        #else:
            #ret = {}
            #for name in sectors:
                #ret[name] = self.__sectors[name]
            #return ret

    #def industries(self):
        #''' Returns a list of all industry names.
        #'''
        #return sorted(self.get_industries().keys())

    #def get_industry(self, name):
        #''' Returns the :class:`Industry` with the given name.
        #'''
        #return self.get_industries()[name]

    #def get_industries(self, industries=None):
        #''' Returns a dict of all Industries. {industry_name: :class:`Industry`}
        #'''
        #if self.__industries == None:
            #self.__industries = {}
            #for sector in self.get_sectors().values():
                #for name, industry in sector.get_industries().items():
                    #self.__industries[name] = industry
        #if industries == None:
            #return self.__industries
        #else:
            #ret = {}
            #for name in industries:
                #ret[name] = self.__industries[name]
            #return ret

    #def get_symbol_industry(self, symbol):
        #''' Returns the Industry() for the given symbol.
        #'''
        #return self.get_instrument(symbol).industry()

    #def get_symbol_sector(self, symbol):
        #''' Returns the Sector() for the given symbol.
        #'''
        #return self.get_symbol_industry(symbol).sector()

    #def update_sectors_and_industries(self, download=False):
        #file_path = os.path.join(self.data_folder(), 'sectors.json')
        #sectors = yql.get_sectors_and_industries(file_path, download)
        #self.__sectors = {}
        #for name, industries in sectors.items():
            #self.__sectors[name] = Sector(name, industries)

    #def update_industry_instruments(self, download=False):
        #file_path = os.path.join(self.data_folder(), 'industries.json')
        #json_industries = yql.get_industry_symbols(file_path, download, self.get_industries())

        #for json_industry in json_industries:
            #industry = self.get_industry(json_industry['name'])
            #industry.set_instruments(json_industry)
        #self.set_instruments()

    #def set_instruments(self):
        #instruments = {}
        #for industry in self.get_industries().values():
            #for symbol, instrument in industry.get_instruments().items():
                #instruments[symbol] = instrument
        #Instruments.set_instruments(self, instruments)

    #def update_instrument_quote_stats(self, instruments=None, download=False):
        #instruments = instruments or self.get_instruments()
        #symbols = [i.symbol() for i in instruments.values()]
        #file_path = os.path.join(self.data_folder(), 'all_instrument_quote_stats.json')
        #instrument_quote_stats = yql.get_symbol_quote_stats(file_path, download, symbols)

        #for json_quote_stats in instrument_quote_stats:
            #symbol = json_quote_stats['Symbol']
            #instrument = self.get_instrument(symbol)
            #instrument.update_quote_stats(json_quote_stats)

    #def update_historical(self, instruments=None, frequency=None):
        #instruments = instruments or self.get_instruments()
        #yahoocsv.bulk_download_historical(instruments, frequency)
