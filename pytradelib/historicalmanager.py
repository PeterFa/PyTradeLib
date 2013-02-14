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
import lz4
import gzip
import importlib
import matplotlib.mlab as mlab

from pytradelib import utils
from pytradelib import settings
from pytradelib.failed import Symbols as FailedSymbols

from pytradelib import bar
from pytradelib import observer

'''
The historical parsing code is implemented as a pluggable generator pipeline:
[See DataManager.__get_bars() and DataManager.__update_symbols() for the code.
Bookmark that caused this experiment: http://www.dabeaz.com/generators-uk/]

    Initialize the generator pipeline with an Instrument or [Instruments]
        \
        V
    file_path(s) -> file_open -> file_to_rows_reader -> row_filter -> parser/drain 
                                                                        |
    Return values from DataManager.get_X_bars():                        V
                            for Instrument --------------> [list of bar.Bar]
                            for Instruments --> {"symbol": [list of bar.Bar]}


It is used by creating an instance of the DataManager class. Some examples:
    symbols =  # > 5K symbols (!)
    parser = DataManager()
    bars = parser.get_bars_dict(symbols)
    bars = parser.get_newest_bars_dict(symbols)
    bars = parser.get_oldest_bars_dict(symbols)
    bars = parser.get_newest_and_oldest_bars(symbols[0]) # or pass a single Instrument
    print bars # or do something useful

'''
## ----- Row Generators --------------------------------------------------------
def symbol_rows(symbol_files):
    for symbol, f in symbol_files:
        data = f.read()
        f.close()
        if settings.DATA_COMPRESSION == 'lz4':
            data = lz4.loads(data)

        # split the file into rows, slicing off the header labels
        csv_rows = data.strip().split('\n')[1:]
        yield (symbol, csv_rows)

# FIXME: For the next 3 functions, we still read the entire file by calling symbol_rows().
# How much is gained by reading only the first/last few lines of the file?
def newest_and_oldest_symbol_rows(symbol_files):
    symbol_rows_ = symbol_rows(symbol_files)
    for symbol, rows in symbol_rows_:
        yield (symbol, [rows[-1], rows[0]])

# oldest date (assumed to be the IPO date)
def oldest_symbol_row(symbol_files):
    symbol_rows_ = symbol_rows(symbol_files)
    for symbol, rows in symbol_rows_:
        yield (symbol, [rows[0]])

# most recent date
def newest_symbol_row(symbol_files):
    symbol_rows_ = symbol_rows(symbol_files)
    for symbol, rows in symbol_rows_:
        yield (symbol, [rows[-1]])

## ----- File Read, Write and Update Generators --------------------------------
def __yield_open_files(tag_file_paths, mode):
    for tag, file_path in tag_file_paths:
        if mode == 'w':
            utils.mkdir_p(os.path.dirname(file_path))
        if settings.DATA_COMPRESSION == 'gz':
            f = gzip.open(file_path, mode)
        elif not settings.DATA_COMPRESSION or settings.DATA_COMPRESSION == 'lz4':
            f = open(file_path, mode)
        yield (tag, f)

def open_files_readable(symbol_file_paths):
    for symbol_file_handle in __yield_open_files(symbol_file_paths, 'r'):
        yield symbol_file_handle

def open_files_writeable(data_file_paths):
    for data_file_handle in __yield_open_files(data_file_paths, 'w'):
        yield data_file_handle

def open_files_updatable(data_file_paths):
    for data_file_handle in __yield_open_files(data_file_paths, 'r+'):
        yield data_file_handle

def write_data(data_files):
    for data, f in data_files:
        if settings.DATA_COMPRESSION == 'lz4':
            data = lz4.dumps(data)
        if data:
            f.write(data)
            symbol = os.path.basename(f.name).split('_')[0]
            f.close()
            yield symbol
        else:
            symbol = os.path.basename(f.name).split('_')[0]
            file_path = f.name
            f.close()
            if os.stat(file_path).st_size == 0:
                os.remove(file_path)
            continue

def process_data_to_update(data_files):
    for update_data, f in data_files:
        if utils.supports_seeking(settings.DATA_COMPRESSION):
            # read the tail of the file and get the newest stored datetime
            new_rows = []
            try: f.seek(-512, 2)
            except IOError: f.seek(0)
            newest_existing_datetime = f.read().split('\n')[-1].split(',')[0]
        elif settings.DATA_COMPRESSION == 'lz4':
            # uncompress entire file, split it into rows and get the newest stored datetime
            new_rows = lz4.loads(f.read()).strip().split('\n')
            newest_existing_datetime = new_rows[-1].split(',')[0] # rely on string sorting for date comparisons

        # only add new rows if the new row's datetime is greater than the newest stored datetime
        update_rows = update_data.strip().split('\n')[1:] # chop the column labels off
        for row in update_rows:
            row_datetime = row.split(',')[0]
            if row_datetime > newest_existing_datetime:
                new_rows.append(row)
        ret_data = '\n'.join(new_rows)

        if utils.supports_seeking(settings.DATA_COMPRESSION):
            # jump to the end of the file
            try: f.seek(-1, 2)
            except IOError: print 'how on earth did you get here?! waaaaaaaaah bugz! :('
            # make sure there's a trailing new-line character at the end
            last_char = f.read()
            if last_char != '\n':
                f.write('\n')
        elif settings.DATA_COMPRESSION == 'lz4':
            # jump to the beginning of the file so we rewrite everything
            f.seek(0)
        yield (ret_data, f)

def yield_pass(data_pairs, *args, **kwargs):
    for pair in data_pairs:
        yield pair

## ----- Historical Data Manager -----------------------------------------------
class DataManager(object):
    def __init__(self):
        self.__initialized_event = observer.Event()
        self.__updated_event = observer.Event()
        self.set_data_provider(settings.DATA_PROVIDER)

    def get_supported_data_providers(self):
        ret = []
        dir_ = os.path.join(os.path.dirname(__file__), 'dataproviders')
        for provider in os.listdir(dir_):
            if os.path.isdir(os.path.join(dir_, provider)):
                ret.append(provider)
        return ret

    def set_data_provider(self, data_provider, default_frequency=None):
        self.__default_frequency = default_frequency or bar.Frequency.DAY
        data_provider = data_provider.lower()
        if data_provider not in self.get_supported_data_providers():
            raise NotImplementedError()
        provider_module = importlib.import_module(
            '.'.join(['pytradelib', 'dataproviders', data_provider]))
        self.__provider = provider_module.Provider()

    def set_bar_filter(self, bar_filter):
        self.__provider.set_bar_filter(bar_filter)

    def get_symbol_initialized_handler(self):
        return self.__initialized_event

    def get_symbol_updated_handler(self):
        return self.__updated_event

# --- get_bars functions -------------------------------------------------------

# FIXME: are all these *really* needed? mainly the ones with oldest seem unnecessary.

    def get_recarray(self, symbol, frequency=None):
        return self.get_recarrays([symbol], frequency)[0]
        
    def get_recarrays(self, symbols, frequency=None):
        frequency = frequency or self.__default_frequency

        # define the pipeline
        symbol_file_handles =  open_files_readable(
            self.__provider.get_symbol_file_paths(symbols, frequency) )

        # start and drain the pipeline
        ret = []
        for symbol, f in symbol_file_handles:
            recarray = mlab.csv2rec(f)
            recarray.sort()
            ret.append(recarray)
        return ret

    def get_bars(self, symbol, frequency=None):
        ret = self.__get_bars([symbol], symbol_rows, frequency, use_bar_filter=True)
        return ret[symbol] # return just the list of bars for the symbol

    def get_bars_dict(self, symbols, frequency=None):
        return self.__get_bars(symbols, symbol_rows, frequency, use_bar_filter=True)

    def get_newest_bar(self, symbol, frequency=None):
        ret = self.__get_bars([symbol], newest_symbol_row, frequency, use_bar_filter=False)
        return ret[symbol][0] # return just the first bar for the symbol

    def get_newest_bars_dict(self, symbols, frequency=None):
        ret = self.__get_bars(symbols, newest_symbol_row, frequency, use_bar_filter=False)
        for symbol, bars in ret.items():
            ret[symbol] = bars[0] # we want just the first bar, not a list of len 1
        return ret

    def get_oldest_bar(self, symbol, frequency=None):
        ret = self.__get_bars([symbol], oldest_symbol_row, frequency, use_bar_filter=False)
        return ret[symbol][0] # return just the last bar for the symbol

    def get_oldest_bars_dict(self, symbols, frequency=None):
        ret = self.__get_bars(symbols, oldest_symbol_row, frequency, use_bar_filter=False)
        for symbol, bars in ret.items():
            ret[symbol] = bars[0] # we want just the last bar, not a list of len 1
        return ret

    def get_newest_and_oldest_bars(self, symbol, frequency=None):
        ret = self.__get_bars([symbol], newest_and_oldest_symbol_rows, frequency, use_bar_filter=False)
        return ret[symbol] # return just a list of [first, last] bars for the symbol

    def get_newest_and_oldest_bars_dict(self, symbols, frequency=None):
        return self.__get_bars(symbols, newest_and_oldest_symbol_rows, frequency, use_bar_filter=False)

# --- symbol initializing functions --------------------------------------------
    def initialize_symbol(self, symbol, frequency=None):
        frequency = frequency or self.__default_frequency
        if self.__provider.symbol_initialized(symbol, frequency):
            print 'symbol %s already initialized!' % symbol
            return None
        for symbol in self.__update_symbols([symbol], frequency):
            self.__initialized_event.emit(symbol, frequency)

    def initialize_symbols(self, symbols, frequency=None):
        frequency = frequency or self.__default_frequency
        initialized = []
        for symbol in symbols:
            if self.__provider.symbol_initialized(symbol, frequency):
                initialized.append(symbol)
        if initialized:
            print 'symbols %s already initialized!' % initialized
            for symbol in initialized:
                symbols.pop(symbols.index(symbol))
            if not symbols:
                return None
        for symbol in self.__update_symbols(symbols, frequency,
            display_progress = True,
            sleep = 4
        ):
            self.__initialized_event.emit(symbol, frequency)

# --- symbol updating functions ------------------------------------------------
    def update_symbol(self, symbol, frequency=None):
        frequency = frequency or self.__default_frequency
        if not self.__provider.symbol_initialized(symbol, frequency):
            print 'symbol %s not initialized yet.' % symbol
            return None
        for symbol in self.__update_symbols([symbol], frequency,
            operation_name = 'update',
            open_files_function = open_files_updatable,
            process_data_update_function = process_data_to_update,
            init = False
        ):
            self.__updated_event.emit(symbol, frequency)

    def update_symbols(self, symbols, frequency=None):
        frequency = frequency or self.__default_frequency
        uninitialized = []
        for symbol in symbols:
            if not self.__provider.symbol_initialized(symbol, frequency):
                uninitialized.append(symbol)
        for symbol in uninitialized:
            symbols.pop(symbols.index(symbol))
        
        if uninitialized:
            print 'symbols %s not initialized yet!' % uninitialized
            if not symbols:
                return None
        for symbol in self.__update_symbols(symbols, frequency,
            operation_name = 'update',
            display_progress = True,
            open_files_function = open_files_updatable,
            process_data_update_function = process_data_to_update,
            init = False,
            sleep = 4
        ):
            self.__updated_event.emit(symbol, frequency)

# --- __private functions ------------------------------------------------------
    def __get_bars(self, symbols, row_generator, frequency, use_bar_filter):
        frequency = frequency or self.__default_frequency

        # define the pipeline
        symbol_rows_ = row_generator( open_files_readable(
            self.__provider.get_symbol_file_paths(symbols, frequency)) )

        # start the pipeline and and drain the results into ret
        ret = {}
        for symbol, rows in symbol_rows_:
            symbol, bars = self.__provider.rows_to_bars(symbol, rows, frequency, use_bar_filter)
            if bars:
                ret[symbol] = bars
        return ret

    def __update_symbols(self, symbols, frequency,
        operation_name = 'download',
        display_progress = False,
        open_files_function = open_files_writeable,
        process_data_update_function = yield_pass,
        init = True,
        sleep = None
    ):
        frequency = frequency or self.__default_frequency
        batch_size = 50
        if frequency == bar.Frequency.MINUTE:
            batch_size = 150
        # load the latest stored datetime for generating urls. this doubles as a flag for initializing vs updating
        symbols = dict((x, None) for x in symbols)
        if frequency != bar.Frequency.MINUTE and not init:
            symbols = dict((x, self.get_newest_bar(x, frequency).get_date_time()) for x in symbols)
        elif not init:
            symbols = dict((x, 1) for x in symbols)
        url_file_paths = [x for x in self.__provider.get_url_file_paths(symbols, frequency)]

        if display_progress:
            total_len = len(url_file_paths)
            current_idx = 0
            last_pct = 0
            print 'starting bulk %s of historical data for %i symbols.' % (operation_name, total_len)
        if not url_file_paths:
            op = ' '
            if display_progress:
                op = ' bulk '
            print 'something went wrong: no urls returned for%s%sing historical data!' % (op, operation_name)
            return

        for urls in utils.batch(url_file_paths, size=batch_size, sleep=sleep):
            # pipeline for downloading data, processing it, and opening the storage files
            data_files = open_files_function(
                self.__provider.process_downloaded_data(
                    self.__provider.verify_downloaded_data(utils.bulk_download(urls)),
                    frequency) )

            # pipeline for saving/updating downloaded data to the storage files
            for symbol in write_data(process_data_update_function(data_files)):
                if display_progress:
                    current_idx += 1
                    pct = int( current_idx / (total_len + 1.0) * 100.0 )
                    if pct != last_pct:
                        last_pct = pct
                        print '%i%%' % pct
                yield symbol
        if display_progress:
            if last_pct != 100:
                print '100%'
