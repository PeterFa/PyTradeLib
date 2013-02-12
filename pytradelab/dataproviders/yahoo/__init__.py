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
import minute
import dayweekmonth

from pytradelab import utils
from pytradelab import settings
from pytradelab import dataproviders
from pytradelab import bar


class Provider(dataproviders.Provider):
    def __init__(self):
        dataproviders.Provider.__init__(self)
        day_week_month_manager = dayweekmonth.YahooFrequencyProvider()
        self.__managers = {
            bar.Frequency.MINUTE: minute.YahooFrequencyProvider(),
            bar.Frequency.DAY: day_week_month_manager,
            bar.Frequency.WEEK: day_week_month_manager,
            bar.Frequency.MONTH: day_week_month_manager,
            }

    def get_csv_column_labels(self, frequency):
        return self.__managers[frequency].get_csv_column_labels()

    def row_to_bar(self, row, frequency):
        return self.__managers[frequency].row_to_bar(row)

    def bar_to_row(self, bar_, frequency):
        return self.__managers[frequency].bar_to_row(bar_)

    def get_url(self, symbol, frequency, latest_date_time=None):
        return self.__managers[frequency].get_url(symbol, frequency, latest_date_time)

    def get_file_path(self, symbol, frequency):
        frequency_lookup = {
            bar.Frequency.MINUTE: 'minute',
            bar.Frequency.DAY: 'day',
            bar.Frequency.WEEK: 'week',
            bar.Frequency.MONTH: 'month',
            }
        extension = utils.get_extension(settings.DATA_COMPRESSION)
        file_path = os.path.join(settings.DATA_DIR, 'symbols', symbol, '%s_%s_all_yahoofinance.%s' % (
            symbol, frequency_lookup[frequency], extension))
        return file_path

    def process_downloaded_data(self, data_file_paths, frequency):
        for data_file_path in self.__managers[frequency].process_downloaded_data(data_file_paths):
            yield data_file_path
