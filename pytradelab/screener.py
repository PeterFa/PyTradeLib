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
import csv

from pytradelab import utils
from pytradelab import settings
from pytradelab import containers
from pytradelab import barfeed
from pytradelab.barfeed import instrumentfeed


class StockScreener(containers.Instruments):
    def __init__(self, name, instruments, bar_feed=None, bar_filter=None):
        containers.Instruments.__init__(self, name)

        if bar_filter == None:
            fromDate = datetime.datetime.now() - datetime.timedelta(days=90)
            bar_filter = csvfeed.DateRangeFilter(fromDate)

        if bar_feed != None:
            # passed barfeeds should already be populated with bars for all symbols in instruments
            self.__feed = bar_feed
        else:
            self.__feed = instrumentfeed.Feed(bar_filter)
            self.__feed.add_bars_from_instruments(instruments)
        containers.Instruments.set_instruments(self, instruments)
        
    def data_folder(self):
        return os.path.join(settings.DATA_DIR, 'watchlists')

    def csv_column_order(self):
        ret = sorted(self.get_instrument().keys())
        ret.insert(0, ret.pop(ret.index('Sector')))
        ret.insert(1, ret.pop(ret.index('Industry')))
        ret.insert(2, ret.pop(ret.index('Symbol')))
        ret.insert(3, ret.pop(ret.index('Name')))
        return ret

    def csv_sort_column(self):
        return 'Sector'

    def csv_sort_descending(self):
        return False

    def on_bars(self, bars):
        pass

    def on_finish(self, bars):
        pass

    def csv_custom_columns(self, instrument):
        pass

    def save_to_csv(self, file_name=None):
        ordered_columns = self.csv_column_order()
        column_header_dict = dict((x, x) for x in ordered_columns)
        instruments = self.get_instruments()

        instrumentCmp = lambda x, y: cmp(
            x[self.csv_sort_column()],
            y[self.csv_sort_column()])

        instruments.sort(instrumentCmp)
        if self.csv_sort_descending():
            instruments.reverse()

        file_name = file_name or '%s.csv' % self.slug()
        file_path = os.path.join(self.data_folder(), file_name)
        utils.mkdir_p(os.path.dirname(file_path))
        with open(file_path, 'w') as f:
            csvwriter = csv.DictWriter(f, fieldnames=ordered_columns, extrasaction='ignore')
            csvwriter.writerow(column_header_dict)
            for instrument in instruments:
                if self.csv_filter(instrument):
                    #csvwriter.writerow(instrument.dict())
                    csvwriter.writerow(instrument.get_values(ordered_columns))

    def __on_bars(self, bars):
        self.on_bars(bars)
        #self.__barsProcessedEvent.emit(self, bars)

    def run(self, save=False):
        try:
            self.__feed.get_new_bars_event().subscribe(self.__on_bars)
            self.__feed.start()
            while not self.__feed.stop_dispatching():
                self.__feed.dispatch()
                # self.on_bars() runs here
            if self.__feed.get_bars() != None:
                self.on_finish(self.__feed.get_bars())
            else:
                raise Exception('Feed was empty')
        finally:
            self.__feed.get_new_bars_event().unsubscribe(self.__on_bars)
            self.__feed.stop()
            self.__feed.join()

        for instrument in self.get_instruments():
            self.csv_custom_columns(instrument)

        if save:
            self.save_to_csv()
