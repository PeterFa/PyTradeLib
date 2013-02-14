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

import time
import datetime
import numpy as np

from collections import defaultdict

from pytradelib import index as index_
from pytradelib import utils
from pytradelib import barfeed
from pytradelib import screener
from pytradelib.barfeed import instrumentfeed
from pytradelib.utils import stats as pyalgotrade_utils


CAPITAL = 10000

class MyScreener(screener.StockScreener):
    def __init__(self, name, instruments, bar_feed=None, bar_filter=None):
        screener.StockScreener.__init__(self, name, instruments, bar_feed, bar_filter)
        self.__pct_changes = defaultdict(list)

    def csv_column_order(self):
        return [
            'Sector',
            'Industry',
            'Symbol',
            'Name',
            'MarketCapitalization',
            'LastTradePriceOnly',
            'AverageDailyVolume',
            'Liquidity',
            'MeanPercentChange',
            'MedianPercentChange',
            ]

    def csv_filter(self, instrument):
        if instrument['Liquidity'] > 1 and instrument['MedianPercentChange'] > 2.5:
            return True
        return False

    def csv_sort_column(self):
        return 'MeanPercentChange'

    def csv_sort_descending(self):
        return True

    def on_bars(self, bars):
        if datetime.datetime.now() - bars.get_date_time() < datetime.timedelta(days=90):
            for symbol in bars.get_symbols():
                this_bar = bars.get_bar(symbol)
                try:
                    day_swing_pct = abs(pyalgotrade_utils.get_change_percentage(
                        this_bar.get_high(), this_bar.get_low()))*100
                except Exception, e:
                    if 'Invalid values' in str(e):
                        pass
                    else:
                        raise e
                else:
                    self.__pct_changes[symbol].append(day_swing_pct)

    def csv_custom_columns(self, instrument):
        instrument['Liquidity'] = None
        try:
            avg_volume_per_minute = float(instrument['AverageDailyVolume'])/(6.5*60)
            num_shares = int(CAPITAL/instrument['LastTradePriceOnly'])
        except (TypeError, ZeroDivisionError):
            pass
        else:
            liquidity = float(avg_volume_per_minute)/num_shares
            instrument['Liquidity'] = liquidity

        instrument['MeanPercentChange'] = None
        instrument['MedianPercentChange'] = None
        percent_changes = self.__pct_changes[instrument.symbol()]
        if percent_changes:
            instrument['MeanPercentChange'] = sum(percent_changes)/float(len(percent_changes))
            instrument['MedianPercentChange'] = np.median(np.asarray(percent_changes))

def run_integrity_check():
    index = index_.Factory()
    instruments = index.get_instruments()
    #instruments = index.get_instruments()[:1000]
    batch_size = len(instruments)/100
    for i, instrument_batch in enumerate(utils.batch(instruments, size=batch_size)):
        instrument_batch = dict(instrument_batch)
        filterFromDate = datetime.datetime.now() - datetime.timedelta(days=99999)
        bar_filter = barfeed.DateRangeFilter(filterFromDate)
        feed = instrumentfeed.Feed(instrument_batch, bar_filter)
        feed.add_bars_from_instruments(instrument_batch)
        print 'batch %i/%i done' % (i + 1, len(instruments)/batch_size + 1)

def run_batched_screener(batch_size):
    index = index_.Factory()

    # run against all instruments
    instruments = index.get_instruments()[:200]
    for instrument in instruments:
        instrument.update_stats()
    for i, batch in enumerate(utils.batch(instruments, batch_size)):
		print 'starting batch %i/%i' % (i, (len(instruments)/batch_size)+1)
		filterFromDate = datetime.datetime.now() - datetime.timedelta(days=100)
		bar_filter = barfeed.DateRangeFilter(filterFromDate)
		symbol_screener = MyScreener('test_list_%i' % i, batch, bar_filter=bar_filter)
		symbol_screener.run(save=True)
		del symbol_screener


def run_screener():
    index = index_.Factory()
    #index.update_historical()

    # run against all instruments
    symbols = index.symbols()
    #instruments = index.get_instruments()
    #instruments = dict(index.get_instruments().items()[:50])

    # or use a custom filter
    filterFromDate = datetime.datetime.now() - datetime.timedelta(days=500)
    bar_filter = barfeed.DateRangeFilter(filterFromDate)
    symbol_screener = MyScreener('test_list_two', symbols, bar_filter=bar_filter)

    ## by sector/industry
    #instruments = index.get_sector('Technology').get_instruments()
    #instruments = index.get_industry('Semiconductor - Broad Line').get_instruments()

    ## by sectors
    #sectors = ['Technology', 'Financial']
    #instruments = {}
    #for industry in index.get_industries(industries).values():
        #instruments.update(industry.get_instruments()

    ## by industries
    #industries = ['Semiconductor - Broad Line', 'Trucking']
    #instruments = {}
    #for industry in index.get_industries(industries).values():
        #instruments.update(industry.get_instruments()

    # by custom list
    #instruments = index.get_instruments(['SYMBOL_ONE', 'TWO', 'THREE', ...])

    # default barfilter is 90 days
    #symbol_screener = MyScreener('test_list_two', instruments)

    # or you can manually load a barfeed/barfilter with data and pass it in like so:
    # bar_feed = pyalgotrade.barfeed.X.Feed()
    # bar_feed.set_bar_filter(bar_filter)
    # bar_feed.addBarsFromX()
    
    #symbol_screener = MyScreener('name', instruments, bar_feed)

    symbol_screener.run(save=True)
    #time.sleep(10)





if __name__ == '__main__':
    def profile(cmd):
        import cProfile
        import pstats
        profFile = 'prof'
        cProfile.run(cmd, profFile)
        p = pstats.Stats(profFile)
        p.strip_dirs().sort_stats("time").print_stats()
    start = datetime.datetime.now()
    print start.strftime('%I:%M:%S %p').lower()

    #profile('run_screener()')
    run_batched_screener(200)
    #run_integrity_check()

    diff = datetime.datetime.now() - start
    total_seconds = diff.seconds + diff.microseconds/1000000.0
    mins_label = 'minutes'
    mins = int(total_seconds/60)
    if mins < 2:
        mins_label = 'minute'
    secs = total_seconds % 60.0

    if total_seconds >= 60:
        print 'total time: %i %s %.2f seconds' % (mins, mins_label, secs)
    else:
        print 'total time: %.3f seconds' % total_seconds
