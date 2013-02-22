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
import lz4
import gzip

import matplotlib.mlab as mlab

from pytradelib import bar
from pytradelib import utils
from pytradelib import observer
from pytradelib import settings
from pytradelib.utils import printf
from pytradelib.data import providers
from pytradelib.data.providers import ProviderFactory
from pytradelib.data.failed import Symbols as FailedSymbols


'''
The historical parsing code is implemented as a pluggable generator pipeline:
[See Reader.__get_bars() and Updater.__update_symbols() for the code.
Bookmark that caused this experiment: http://www.dabeaz.com/generators-uk/]

    Initialize the generator pipeline with an Instrument or [Instruments]
        |
        V
 file_path(s) -> file_open -> file_to_rows_reader -> row_filter -> parser/drain
                                                                        |
    Return values from Reader.get_X_bars():                             V
                              for Instrument --------------> [list of bar.Bar]
                              for Instruments --> {"symbol": [list of bar.Bar]}
'''

class CSVRowMixin(object):
    def symbol_rows(self, symbol_contexts):
        for symbol, context in symbol_contexts:
            f = context.pop('_open_file')
            data = f.read()
            f.close()
            if settings.DATA_COMPRESSION == 'lz4':
                data = lz4.loads(data)

            # split the file into rows, slicing off the header labels
            csv_rows = data.strip().split('\n')[1:]
            yield csv_rows, context

    # FIXME: For the next three functions, we still read the entire file. How much
    # is gained by reading only the first/last few lines of the file?

    def newest_and_oldest_symbol_rows(self, symbol_contexts):
        symbol_rows = self.symbol_rows(symbol_contexts)
        for symbol, rows in symbol_rows:
            yield ([rows[-1], rows[0]], context)

    # FIXME: For the next two functions, optionally return count bars from beg/end?

    # oldest date (assumed to be the IPO date)
    def oldest_symbol_row(self, symbol_contexts):
        symbol_rows = self.symbol_rows(symbol_contexts)
        for symbol, rows in symbol_rows:
            yield ([rows[0]], context)

    # most recent date
    def newest_symbol_row(self, symbol_contexts):
        symbol_rows = self.symbol_rows(symbol_contexts)
        for symbol, rows in symbol_rows:
            yield ([rows[-1]], context)


class Reader(providers.OpenFilesMixin, CSVRowMixin):
    def __init__(self):
        self.set_data_provider(settings.DATA_STORE_FORMAT)

    def set_data_provider(self, data_provider, default_frequency=None):
        self._default_frequency = default_frequency or bar.Frequency.DAY
        self._data_reader = ProviderFactory.get_data_provider(data_provider)

    def set_bar_filter(self, bar_filter):
        self._data_reader.set_bar_filter(bar_filter)

    def get_recarray(self, symbol, frequency=None):
        return self.get_recarrays([symbol], frequency)[0]
        
    def get_recarrays(self, symbols, frequency=None):
        frequency = frequency or self._default_frequency

        # define the pipeline
        symbol_contexts = \
            self.open_files_readable(
                self._data_reader.get_file_paths([(symbol,
                                                  {'frequency': frequency})
                                                  for symbol in symbols]))

        # start and drain the pipeline
        ret = []
        for symbol, context in symbol_contexts:
            f = context.pop('_open_file')
            recarray = mlab.csv2rec(f)
            recarray.sort()
            ret.append(recarray)
            f.close()
        return ret

    def get_bars(self, symbol, frequency=None):
        ret = self.__get_bars(
            [symbol], self.symbol_rows, frequency, use_bar_filter=True)
        return ret[symbol] # return just the list of bars for the symbol

    def get_bars_dict(self, symbols, frequency=None):
        return self.__get_bars(
            symbols, self.symbol_rows, frequency, use_bar_filter=True)

    # FIXME: are all the following public functions *really* needed?
    def get_newest_bar(self, symbol, frequency=None):
        ret = self.__get_bars(
            [symbol], self.newest_symbol_row, frequency, use_bar_filter=False)
        return ret[symbol][0] # return just the first bar for the symbol

    def get_newest_bars_dict(self, symbols, frequency=None):
        ret = self.__get_bars(
            symbols, self.newest_symbol_row, frequency, use_bar_filter=False)
        for symbol, bars in ret.items():
            ret[symbol] = bars[0] # return just the first bar for the symbols
        return ret

    def get_oldest_bar(self, symbol, frequency=None):
        ret = self.__get_bars(
            [symbol], self.oldest_symbol_row, frequency, use_bar_filter=False)
        return ret[symbol][0] # return just the last bar for the symbol

    def get_oldest_bars_dict(self, symbols, frequency=None):
        ret = self.__get_bars(
            symbols, self.oldest_symbol_row, frequency, use_bar_filter=False)
        for symbol, bars in ret.items():
            ret[symbol] = bars[0] # return just the last bar for the symbols
        return ret

    def get_newest_and_oldest_bars(self, symbol, frequency=None):
        ret = self.__get_bars([symbol], self.newest_and_oldest_symbol_rows,
                               frequency, use_bar_filter=False)
        return ret[symbol] # return a list [first_bar, last_bar] for the symbol

    def get_newest_and_oldest_bars_dict(self, symbols, frequency=None):
        return self.__get_bars(symbols, self.newest_and_oldest_symbol_rows,
                               frequency, use_bar_filter=False)

    def __get_bars(self, symbols, row_generator, frequency, use_bar_filter):
        frequency = frequency or self._default_frequency

        # define the pipeline
        row_contexts = \
            row_generator(
                self.open_files_readable(
                    self._data_reader.get_file_paths(symbols, frequency)))

        # start the pipeline and and drain the results into ret
        ret = {}
        for rows, context in row_contexts:
            symbol, bars = self._data_reader.rows_to_bars(context['symbol'],
                                                          rows,
                                                          frequency,
                                                          use_bar_filter)
            if bars:
                ret[symbol] = bars
        return ret


class Updater(providers.OpenFilesMixin):
    def __init__(self, db):
        self._updated_event = observer.Event()
        self._db = db
        self.set_provider_formats(settings.DATA_PROVIDER,
                                  settings.DATA_STORE_FORMAT)

    def set_provider_formats(self, downloader, writer, default_frequency=None):
        self._downloader_format = downloader.lower()
        self._writer_format = writer.lower()
        self._default_frequency = default_frequency or bar.Frequency.DAY

        self._data_downloader = ProviderFactory.get_data_provider(
                                                    self._downloader_format)
        self._data_writer = ProviderFactory.get_data_provider(
                                                    self._writer_format)

    def get_update_event_handler(self):
        return self._updated_event

    def initialize_symbol(self, symbol, frequency=None):
        self.initialize_symbols([symbol], frequency)

    def initialize_symbols(self, symbols, frequency=None):
        frequency = frequency or self._default_frequency
        initialized = [x for x in symbols
                       if self._data_writer.symbol_initialized(x, frequency)\
                       or x in FailedSymbols]
        if initialized:
            printf('%i symbols %s already initialized!' % (
                len(initialized), initialized))
            for symbol in initialized:
                symbols.pop(symbols.index(symbol))

        if not symbols:
            printf('no symbols to initialize.')
            return None
        for context in self.__update_symbols(symbols, frequency, sleep=1):
            self._updated_event.emit(context)

    def update_symbol(self, symbol, frequency=None):
        self.update_symbols([symbol], frequency)

    def update_symbols(self, symbols, frequency=None):
        frequency = frequency or self._default_frequency
        uninitialized = \
            [x for x in symbols
             if x not in FailedSymbols \
             and not self._data_writer.symbol_initialized(x, frequency)]
        if uninitialized:
            printf('%i symbols %s not initialized yet!' % (
                len(uninitialized), uninitialized))
            for symbol in uninitialized:
                symbols.pop(symbols.index(symbol))
            if not symbols:
                return None

        for context in self.__update_symbols(symbols, frequency,
            operation_name='update',
            open_files_function=self.open_files_updatable,
            process_data_update_function=self._data_writer.update_data,
            init=False,
            sleep=1
        ):
            self._updated_event.emit(context)

    def __process_data_to_initialize(self, data_contexts):
        for rows, context in data_contexts:
            rows.insert(0, self._data_writer.get_csv_column_labels(
                context['frequency']))
            yield rows, context

    def __update_symbols(self, symbols, frequency,
        operation_name='download',
        open_files_function=None,
        process_data_update_function=None,
        init=True,
        sleep=None
    ):
        '''
        This function contains the actual pipeline logic for downloading,
        initializing and updating symbols' data. It can display the rough
        progress of bulk operation to stdout using display_progress.
        '''
        open_files_function = \
            open_files_function or self.open_files_writeable
        process_data_update_function = \
            process_data_update_function or self.__process_data_to_initialize
        frequency = frequency or self._default_frequency
        batch_size = 200 if frequency is not bar.Frequency.MINUTE else 500
        sleep = sleep if frequency is not bar.Frequency.MINUTE else None

        display_progress = True if len(symbols) > 1 else False
        # Load the latest stored datetime for the requested combination of
        # symbols and frequency. This doubles as a flag for init vs update.\
        symbol_contexts = [
            (x, {'symbol': x, 'frequency': frequency, 'from_date_time': None})
            for x in symbols]
        if frequency != bar.Frequency.MINUTE and not init:
            for symbol, context in symbol_contexts:
                context['from_date_time'] = self._db.get_updated(bar.FrequencyToStr[frequency], symbol)
        elif not init:
            for symbol, context in symbol_contexts:
                context['from_date_time'] = True # set update over init

        url_contexts = self._data_downloader.get_urls(symbol_contexts)
        if not url_contexts:
            op = ' ' if not display_progress else ' bulk '
            raise Exception('no urls returned for%s%sing historical data!' % (
                                                 op, operation_name))
        elif display_progress:
            total_len = len(url_contexts)
            current_idx = 0
            last_pct = 0
            printf('starting bulk %s of historical data for %i symbols.' % (
                                 operation_name, total_len))
            sys.stdout.flush()

        for context in self.__bulk_dl_and_save(url_contexts,
            process_data_update_function, open_files_function,
            batch_size, sleep
        ):
            if display_progress:
                current_idx += 1
                pct = int(current_idx / (total_len + 1.0) * 100.0)
                if pct != last_pct:
                    last_pct = pct
                    printf('%i%%' % pct)

            yield context

        if display_progress:
            if last_pct != 100:
                printf('100%')

    def __bulk_dl_and_save(self,
        url_contexts,
        process_data_update_function,
        open_files_function,
        batch_size=None,
        sleep=None
    ):
        # download, process and update/save
        for url_contexts in utils.batch(url_contexts, size=batch_size, sleep=sleep):
            # pipeline for downloading data and preprocessing it
            data_contexts = \
                self._data_downloader.process_downloaded_data(
                    self._data_downloader.verify_download(
                        utils.bulk_download(url_contexts)))

            # if necessary, convert downloaded format into a new storage format
            if self._data_downloader.name != self._data_writer.name:
                data_contexts = \
                    self._data_downloader.convert_data(data_contexts, self._data_writer)

            # drain for opening files and saving/updating downloaded data
            for context in self._data_writer.save_data(
                process_data_update_function(
                    open_files_function(data_contexts))
            ):
                yield context
        yield None # poison pill to signal end of downloads

class StatsUpdater(object):
    def __init__(self):
        self._downloader = 'YahooStats()' # FIXME

    def update_stats(self, symbols):
        urls = self._downloader.get_urls(symbols)
        symbol_stats = \
            self._downloader.process_downloaded_data(
                self._downloader.verify_download(
                    utils.bulk_download(urls)))
        self._db.insert_or_update_stats([d for d in symbol_stats])
