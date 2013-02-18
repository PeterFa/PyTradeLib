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
import minute
import dayweekmonth

from pytradelib import bar
from pytradelib import utils
from pytradelib import settings
from pytradelib.data.providers import historical


class Provider(historical.Provider):
    def __init__(self):
        historical.Provider.__init__(self)
        day_week_month_manager = dayweekmonth.YahooFrequencyProvider()
        self.__managers = {
            bar.Frequency.MINUTE: minute.YahooFrequencyProvider(),
            bar.Frequency.DAY: day_week_month_manager,
            bar.Frequency.WEEK: day_week_month_manager,
            bar.Frequency.MONTH: day_week_month_manager,
            }

    def name(self):
        return 'Yahoo'

    def get_csv_column_labels(self, frequency):
        return self.__managers[frequency].get_csv_column_labels()

    def row_to_bar(self, row, frequency):
        return self.__managers[frequency].row_to_bar(row)

    def bar_to_row(self, bar_, frequency):
        return self.__managers[frequency].bar_to_row(bar_)

    def get_url(self, symbol, frequency, latest_date_time=None):
        return self.__managers[frequency].get_url(symbol, frequency, latest_date_time)

    def get_file_path(self, symbol, frequency):
        file_name = utils.get_historical_file_name(
            symbol, frequency, self.name(), settings.DATA_COMPRESSION)
        return os.path.join(settings.DATA_DIR, 'symbols', file_name)

    def process_downloaded_data(self, data_file_paths, frequency):
        for data_file_path in self.__managers[frequency].process_downloaded_data(data_file_paths):
            yield data_file_path
