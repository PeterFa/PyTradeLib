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

from pytradelib import bar
from pytradelib import utils
from pytradelib import barfeed
from pytradelib import settings
from pytradelib.data import providers
from pytradelib.utils import printf
from pytradelib.failed import Symbols as FailedSymbols


class Provider(providers.Provider):
    def __init__(self):
        self.__bar_filter = None

    @property
    def name(self):
        raise NotImplementedError()

    def set_bar_filter(self, bar_filter):
        self.__bar_filter = bar_filter

    @utils.lower
    def get_url(self, symbol, context):
        raise NotImplementedError()

    def get_urls(self, symbol_contexts):
        ret = []
        for symbol, context in symbol_contexts:
            if symbol not in FailedSymbols:
                url = self.get_url(symbol, context)
                context['file_path'] = self.get_file_path(symbol, context['frequency'])
                ret.append((url, context))
        return ret

    @utils.lower
    def get_file_path(self, symbol, context):
        raise NotImplementedError()

    def get_file_paths(self, symbol_contexts):
        for symbol, context in symbol_contexts:
            context['symbol'] = symbol
            context['file_path'] = self.get_file_path(symbol, frequency)
            yield symbol, context

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
            elif isinstance(self.__bar_filter, barfeed.DateRangeFilter):
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
            rows.append(self.bar_to_row(bar_, frequency))
        return symbol, rows

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

    def verify_download(self, data_contexts):
        for data, context in data_contexts:
            if 'error' in context and context['error']:
                FailedSymbols.add_failed(context['symbol'], context['error'])
                continue
            else:
                yield data, context

    def process_downloaded_data(self, data_contexts):
        # The yielded data should be a list of csv-delimited bar-rows,
        # ordered with the oldest data at 0 and the most recent data at the end

        # the default implementation is to strip trailing white-space, split by
        # newlines, chop off the first row and yield. Override if necessary.
        for data, context in data_contexts:
            yield (data.strip().split('\n')[1:], context)

    def convert_data(self, data_contexts, to_provider):
        for rows, context in data_contexts:
            symbol = context['symbol']
            frequency = context['frequency']
            context['file_path'] = to_provider.get_file_path(symbol, frequency)
            header = rows.pop(0)
            symbol, bars = self.rows_to_bars(symbol, rows, frequency)
            symbol, rows = to_provider.bars_to_rows(symbol, bars, frequency)
            rows.insert(0, to_provider.get_csv_column_labels(frequency))
            yield (rows, context)

    def update_data(self, data_contexts):
        for update_rows, context in data_contexts:
            f = context['_open_file']
            # read existing data, relying on string sorting for date comparisons
            if utils.supports_seeking(settings.DATA_COMPRESSION):
                # read the tail of the file to rows and get newest stored datetime
                new_rows = []
                try: f.seek(-512, 2)
                except IOError: f.seek(0)
                newest_existing_datetime = f.read().split('\n')[-1].split(',')[0]

            elif settings.DATA_COMPRESSION == 'lz4':
                # read entire file to rows and get newest stored datetime
                new_rows = lz4.loads(f.read()).strip().split('\n')
                newest_existing_datetime = new_rows[-1].split(',')[0]

            # only add new rows if row datetime is greater than stored datetime
            for row in update_rows:
                row_datetime = row.split(',')[0]
                if row_datetime > newest_existing_datetime:
                    new_rows.append(row)

            # seek to the proper place in the file in preparation for write_data
            if utils.supports_seeking(settings.DATA_COMPRESSION):
                # jump to the end of the file so we only update existing data
                try: f.seek(-1, 2)
                except IOError: printf('unexpected file seeking bug :(', f.name)
                # make sure there's a trailing new-line character at the end
                last_char = f.read()
                if last_char != '\n':
                    f.write('\n')
            elif settings.DATA_COMPRESSION == 'lz4':
                # jump to the beginning of the file so we rewrite everything
                f.seek(0)

            yield (new_rows, context)

    def save_data(self, data_contexts):
        for rows, context in data_contexts:
            f = context.pop('_open_file')
            if rows:
                bar_ = self.row_to_bar(
                    rows[-1], context['frequency'])
                if isinstance(bar_, bar.Bar):
                    context['to_date_time'] = bar_.get_date_time()
                else:
                    printf('latest datetime for %s was invalid: %s' % (
                                           context['symbol'], bar_))

                data = '%s\n' % '\n'.join(rows)
                if settings.DATA_COMPRESSION == 'lz4':
                    data = lz4.dumps(data)

                f.write(data)
                f.close()
                yield context
            else:
                file_path = f.name
                f.close()
                if os.stat(file_path).st_size == 0:
                    os.remove(file_path)
                continue

