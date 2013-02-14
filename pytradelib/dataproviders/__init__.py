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
from pytradelib.failed import Symbols as FailedSymbols
from pytradelib.barfeed import csvfeed


## ----- Data Provider Base Class (to be subclassed by data providers) ----------
class Provider(object):
    def __init__(self):
        self.__bar_filter = None

    def set_bar_filter(self, bar_filter):
        self.__bar_filter = bar_filter

    @utils.lower
    def symbol_initialized(self, symbol, frequency):
        if os.path.exists(self.get_file_path(symbol, frequency)):
            return True
        return False

    def get_csv_column_labels(self, frequency):
        raise NotImplementedError()

    def row_to_bar(self, row, frequency):
        raise NotImplementedError()

    @utils.lower
    def rows_to_bars(self, symbol, rows, frequency, use_bar_filter=True):
        bars = []
        errors = False
        for i, row in enumerate(rows):
            # parse the row and check the bar for errors
            bar_ = self.row_to_bar(row, frequency)
            if not self.__verify_bar(symbol, bar_, i):
                errors = True # keep parsing bars after errors (primarily to search for more erors)
            
            if not use_bar_filter:
                bars.append(bar_)

            # check if we should add the bar when using a DateRangeFilter
            elif isinstance(self.__bar_filter, csvfeed.DateRangeFilter):
                if self.__bar_filter.includeBar(bar_):
                    bars.append(bar_)
                # make sure we've gotten to the start of the date range before breaking
                elif len(bars) > 0:
                    break

            # otherwise check if we should add bar_ against some other type of BarFilter
            elif self.__bar_filter == None or self.__bar_filter.includeBar(bar_):
                bars.append(bar_)
        if errors:
            return (symbol, None)
        return (symbol, bars)

    def bar_to_row(self, bar_, frequency):
        raise NotImplementedError()

    @utils.lower
    def bars_to_rows(self, symbol, bars, frequency):
        rows = []
        for bar_ in bars:
            rows.append(self.bar_to_row(bar_))
        return rows

    def __verify_bar(self, symbol, bar_, i):
        if isinstance(bar_, str):
            line_number = '%i' % (i + 2) # +1 for the header row and +1 because i is 0-indexed
            if symbol not in FailedSymbols:
                FailedSymbols.add_failed(symbol, {line_number: bar_})
            else:
                previous_errors = FailedSymbols.get_error(symbol)
                previous_errors.update({line_number: bar_})
                FailedSymbols.add_failed(symbol, previous_errors)
            return False
        return True

    def verify_downloaded_data(self, data_tags):
        for data, tags in data_tags:
            file_path = tags['tag']['file_path']
            symbol = tags['tag']['symbol']
            if 'error' in tags:
                FailedSymbols.add_failed(symbol, tags['error'])
                continue
            else:
                yield (data, file_path)

    def process_downloaded_data(self, data_file_paths, frequency):
        # the yielded csv (comma/semicolon/etc) data should be a '\n' newline-delimited
        # string with the following properties:
        # - the first line should be the ordered column labels, csv-delimited
        # - the rest of the lines should be csv-delimited bar-rows, ordered with
        #     the oldest data at the beginning and the most recent data at the end
        # - there should be no trailing white-space at the end of the string
        
        # the default implementation is to strip trailing white-space and yield;
        # override if more complex parsing is required
        for data, file_path in data_file_paths:
            yield (data.strip(), file_path)

    #def process_data_to_update(self, data_files, frequency):
        #raise NotImplementedError()

    @utils.lower
    def get_url(self, symbol, frequency):
        raise NotImplementedError()

    @utils.lower
    def get_file_path(self, symbol, frequency):
        raise NotImplementedError()

    def get_symbol_file_paths(self, symbols, frequency):
        for symbol in symbols:
            file_path = self.get_file_path(symbol, frequency)
            if symbol not in FailedSymbols and os.path.exists(file_path):
                yield (symbol, file_path)

    def get_url_file_paths(self, symbol_times, frequency):
        for symbol, latest_date_time in symbol_times.items():
            if symbol not in FailedSymbols:
                url = self.get_url(symbol, frequency, latest_date_time)
                file_path = self.get_file_path(symbol, frequency)
                if latest_date_time or not os.path.exists(file_path):
                    yield (url, {'symbol': symbol, 'file_path': file_path})
