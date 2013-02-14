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

import datetime
import calendar

from pytradelab import utils
from pytradelab import bar


class YahooFrequencyProvider(object):
    def __init__(self):
        self.__columns = ['DateTime', 'Close', 'High', 'Low', 'Open', 'Volume']

    def get_csv_column_labels(self):
        return ','.join(self.__columns)

    def row_to_bar(self, row):
        row = row.split(',')
        date = datetime.datetime.fromtimestamp(int(row[0]))
        close = float(row[1])
        high = float(row[2])
        low = float(row[3])
        open_ = float(row[4])
        volume = float(row[5])
        try:
            return bar.Bar(date, open_, high, low, close, volume, close)
        except AssertionError, e:
            return str(e)

    def bar_to_row(self, bar_):
        ret = ','.join([
            '%i' % calendar.timegm(bar_.get_date_time().timetuple()),
            '%.2f' % bar_.get_close(),
            '%.2f' % bar_.get_high(),
            '%.2f' % bar_.get_low(),
            '%.2f' % bar_.get_open(),
            '%i' % bar_.get_volume()
            ])
        return ret

    @utils.lower
    def get_url(self, symbol, frequency, from_date=None):
        raise NotImplementedError("Hint: Use Firebug in places where you "\
            "might expect AJAX calls for intraday data. Implement at your own"\
            " risk; I'm not entirely sure what Yahoo's TOS are for using it.")

    def process_downloaded_data(self, data_file_paths):
        # minutely data has a big, multi-row header, and only comes one day at a time
        # times are formatted in seconds from the unix epoch; convert them to datetime
        for data, file_path in data_file_paths:
            data_rows = data.strip().split('\n')
            # grab the column labels from the middle of the header and find the start index of the data
            for i, row in enumerate(data_rows):
                #if i == 0 and '/fb/' in row:
                    #symbol = True
                if row.startswith('values:'):
                    row = row[len('values:'):]
                    column_labels = ','.join([x.title() for x in row.split(',')])
                elif row.startswith('volume'):
                    # chop off the entire header so data_rows contains only bar rows
                    data_rows = data_rows[i+1:]
                    break

            # date conversions # FIXME: store in UTC
            try:
                for i, row in enumerate(data_rows):
                    columns = row.split(',')
                    dt = datetime.datetime.fromtimestamp(int(columns[0]))
                    columns[0] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    data_rows[i] = ','.join(columns)
            except Exception, e:
                print str(e)
                continue

            # insert the column labels at the top of the data rows
            data_rows.insert(0, column_labels)
            if len(data_rows) > 2:
                latest_quote = data_rows.pop(-1)
                print 'latest_quote', latest_quote, 'FIXME: emit this bar' 
            yield ('\n'.join(data_rows), file_path)
