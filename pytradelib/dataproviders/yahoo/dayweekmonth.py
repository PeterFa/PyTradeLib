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

import datetime

from pytradelib import utils
from pytradelib import bar


class YahooFrequencyProvider(object):
    def __init__(self):
        self.__columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'AdjClose']

    def get_csv_column_labels(self):
        return ','.join(self.__columns)

    def row_to_bar(self, row):
        row = row.split(',')
        dt = row[0]
        date = datetime.datetime(int(dt[:4]), int(dt[5:7]), int(dt[8:10]))
        open_ = float(row[1])
        high = float(row[2])
        low = float(row[3])
        close = float(row[4])
        volume = float(row[5])
        adj_close = float(row[6])
        try:
            return bar.Bar(date, open_, high, low, close, volume, adj_close)
        except AssertionError, e:
            return str(e)

    def bar_to_row(self, bar_):
        ret = ','.join([
            bar_.get_date_time().strftime('%Y-%m-%d'),
            '%.2f' % bar_.get_open(),
            '%.2f' % bar_.get_high(),
            '%.2f' % bar_.get_low(),
            '%.2f' % bar_.get_close(),
            '%i' % bar_.get_volume(),
            '%.2f' % bar_.get_adj_close()
            ])
        return ret

    @utils.lower
    def get_url(self, symbol, frequency, from_date=None):
        from_date = from_date or datetime.date(1800, 1, 1)
        to_date = datetime.date.today()
        if from_date == to_date:
            from_date -= datetime.timedelta(days=1)
        if frequency not in [bar.Frequency.DAY, bar.Frequency.WEEK, bar.Frequency.MONTH]:
            frequency = bar.Frequency.DAY
        url = 'http://ichart.finance.yahoo.com/table.csv?s=%s&a=%d&b=%d&c=%d&d=%d&e=%d&f=%d&g=%s&ignore=.csv' % (
            symbol, from_date.month-1, from_date.day, from_date.year,
            to_date.month-1, to_date.day, to_date.year, frequency)
        return url

    def process_downloaded_data(self, data_file_paths):
        for data, file_path in data_file_paths:
            # keep the column labels at the top but reverse the sort order of data rows
            # (we want the most recent data to be at the end of the file)
            data_rows = data.strip().split('\n')
            column_labels = data_rows.pop(0)
            data_rows.reverse()
            data_rows.insert(0, column_labels)
            yield ('\n'.join(data_rows), file_path)
