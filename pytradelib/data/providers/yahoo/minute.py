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
import calendar

from pytradelib import utils
from pytradelib import bar
from pytradelib import settings
from pytradelib.failed import Symbols as FailedSymbols


class YahooFrequencyProvider(object):
    '''
    This class (almost) implements support for minutely bars from Yahoo. They
    are advertised as "realtime," but obviously there are quite a few steps
    between us, Yahoo and the source. Lag varies from <1 minute to upwards of
    >10 minutes behind the market (though 3-5 minutes behind seems much more
    common when things are acting sluggish).

    All you need to do to finish the implementation is return a valid URL from
    get_url() for a given symbol. See get_url() as it is now for a hint on how.
    '''
    def __init__(self):
        self.__columns = ['DateTime', 'Close', 'High', 'Low', 'Open', 'Volume']

    def get_csv_column_labels(self):
        return ','.join(self.__columns)

    def row_to_bar(self, row):
        row = row.split(',')
        try:
            date = datetime.datetime.fromtimestamp(int(row[0]))
        except ValueError:
            date = datetime.datetime.strptime(row[0], settings.DATE_FORMAT)
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
            bar_.get_date_time().strftime(settings.DATE_FORMAT),
            '%.2f' % bar_.get_close(),
            '%.2f' % bar_.get_high(),
            '%.2f' % bar_.get_low(),
            '%.2f' % bar_.get_open(),
            '%i' % bar_.get_volume()
            ])
        return ret

    @utils.lower
    def get_url(self, symbol, context=None):
        url = "--> fill me in with %s's url <--" % symbol # context unused
        raise NotImplementedError("Hint: Use Firebug in places where you "\
            "might expect AJAX calls for intraday data. Implement at your own"\
            " risk; I'm not entirely sure what Yahoo's TOS are for using this.")
        return url

    def verify_download(self, data, context):
        rows = data.strip().split('\n')
        idx = 15 if len(rows) > 15 else len(rows)
        for i, row in enumerate(rows[:idx]):
            if row.startswith('error'):
                FailedSymbols.add_failed(context['symbol'],
                                            rows[i+1][len('message:'):])
                return False
        return True

    def process_downloaded_data(self, data, context):
        # minutely data has a big, multi-row header and only comes one day at
        # a time. datetimes are formatted in seconds from the unix epoch.

        # find the start index of the bar-rows
        data_rows = data.strip().split('\n')
        for i, row in enumerate(data_rows):
            if row.startswith('volume'):
                # chop off the header so data_rows contains only bar-rows
                data_rows = data_rows[i+1:]
                break

        # date conversions
        # FIXME: store in UTC
        # FIXME: round bars to even minutes?
        # FIXME: add "fake" missing bars?
        #        maybe OHLC == avg prev/next closes and volume == None ?
        for i, row in enumerate(data_rows):
            columns = row.split(',')
            dt = datetime.datetime.fromtimestamp(int(columns[0]))
            columns[0] = dt.strftime(settings.DATE_FORMAT)
            data_rows[i] = ','.join(columns)

        now = datetime.datetime.now().time() # FIXME: UTC
        if len(data_rows) > 1 \
            and (datetime.time(9, 30) < now < datetime.time(16)):
            # FIXME: emit this bar
            context['latest_quote'] = data_rows.pop(-1)
        return data_rows, context
