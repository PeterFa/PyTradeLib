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

import numpy as np
import talib
from talib import abstract
from collections import OrderedDict

from pytradelib import dataseries
from pytradelib import technical


# Returns the last values of a dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def value_ds_to_numpy(ds, count):
    values = ds.get_values(count)
    if values == None:
        return None
    return np.array([float(value) for value in values])

# Returns the last open values of a bar dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def bar_ds_open_to_numpy(barDs, count):
    return value_ds_to_numpy(barDs.get_open_data_series(), count)

# Returns the last high values of a bar dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def bar_ds_high_to_numpy(barDs, count):
    return value_ds_to_numpy(barDs.get_high_data_series(), count)

# Returns the last low values of a bar dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def bar_ds_low_to_numpy(barDs, count):
    return value_ds_to_numpy(barDs.get_low_data_series(), count)

# Returns the last close values of a bar dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def bar_ds_close_to_numpy(barDs, count):
    return value_ds_to_numpy(barDs.get_close_data_series(), count)

# Returns the last volume values of a bar dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def bar_ds_volume_to_numpy(barDs, count):
    return value_ds_to_numpy(barDs.get_volume_data_series(), count)


class Function(abstract.Function):
    ''' A thin wrapper around abstract.Function for converting data inputs of
    BarDataSeries into the expected input of a dict of numpy arrays.
    '''
    def __init__(self, function_name):
        abstract.Function.__init__(self, function_name)
        self.__bar_ds = None
        # lookup for converting bar price series into numpy arrays
        self.__bar_ds_to_np = { 'open': bar_ds_open_to_numpy,
                                'high': bar_ds_high_to_numpy,
                                'low': bar_ds_low_to_numpy,
                                'close': bar_ds_close_to_numpy,
                                'volume': bar_ds_volume_to_numpy }

    def get_data_series(self):
        return self.__bar_ds

    def set_data_series(self, bar_ds):
        self.__bar_ds = bar_ds
        self.set_input_arrays(bar_ds)

    def set_input_arrays(self, input_data):
        # first call the super's implementation. If it returns False, check if
        # we can handle the input_data.
        if abstract.Function.set_input_arrays(self, input_data):
            return True
        elif isinstance(input_data, dataseries.BarDataSeries):
            input_arrays = abstract.Function.get_input_arrays(self)
            for input_ in input_arrays:
                ds_to_np = self.__bar_ds_to_np[input_]
                input_arrays[input_] = ds_to_np(input_data, len(input_data))
            abstract.Function.set_input_arrays(self, input_arrays)
            return True
        return False


class TalibCache(object):
    ''' A simple cache for holding (pre)calculated values from a function.
    NOTE: The user of the cache is responsible for handling coherency. (!)
    '''
    def __init__(self, data=None):
        self.__data = None
        self.set_data(data)

    def initialized(self):
        if self.__data:
            return True
        return False

    def set_data(self, data):
        if data:
            self.__data = OrderedDict()
            for output in data:
                values = data[output]
                self.__data[output] = [x for x in values]

    def __len__(self):
        if self.__data:
            return len(self.__data[self.__data.keys()[0]])
        return 0

    def __getitem__(self, idx):
        if idx < 0 or idx > len(self):
            raise IndexError()
        ret = OrderedDict()
        for output in self.__data:
            value = self.__data[output][idx]
            if np.isnan(value):
                return None
            ret[output] = value
        return ret

    def __setitem__(self, idx, value):
        raise NotImplementedError()

    def append(self, data):
        # FIXME this function blindly appends data; perhaps pass in the absolute index too.....
        for output in data:
            for value in data[output]:
                if not np.isnan(value):
                    self.__data[output].append(value)


class BarDataSeriesFilter(dataseries.BarDataSeries):
    def __init__(self, function_name, source_ds, cache_ds=None, *args, **kwargs):
        ''' A wrapper around dataseries.BarDataSeries for TALIB functions. It is
        meant to more-or-less mimick pyalgotrade.technical.DataSeriesFilter.

        FIXME It requires two arguments, the source dataseries and the cache dataseries:
        - The source_ds should come from a barfeed so that when the barfeed
        dispatches, getValue() will return the correct corresponding value.
        Therefore, note that the source_ds will usually be empty to start with.
        Also, this class only returns values for bars in the source dataseries,
        even if 'future' values exist in the cache. This is on purpose; we
        shouldn't be able to see the future while backtesting!

        - The cache_ds on the otherhand, should be populated with bars, starting
        from the same index (ie datetime) as the source_ds. The symbol and data
        frequency of the cache_ds must also be the same as the source_ds's.

        Finally, you can pass optional positional/keyword arguments after the
        dataseries inputs corresponding to the function's parameters.

        WARNING: Once again the cache and source dataseries must be for the same
        symbol and data frequency, and must share the same starting datetime.
        If you change one dataseries, be sure to immediately update the other,
        before calling any of this class's other functions.
        '''
        dataseries.BarDataSeries.__init__(self)
        self.__func_handle = Function(function_name)
        self.__source_ds = source_ds
        self.__cache_ds = cache_ds
        self.__cache = TalibCache()
        self.__cache_dirty = False

        self.set_data_series(source_ds, cache_ds)
        self.set_function_parameters(*args, **kwargs)

    def set_data_series(self, source_ds, cache_ds=None):
        self.__source_ds = source_ds
        self.__cache_ds = cache_ds
        self.__cache.set_data(None) # erase the cache when the dataseries changes
        self.__cache_dirty = False

    def set_function_parameters(self, *args, **kwargs):
        self.__func_handle.set_function_parameters(*args, **kwargs)
        self.__cache.set_data(None)
        self.__cache_dirty = False

    def get_func_handle(self):
        return self.__func_handle

    def getWindowSize(self):
        return self.__func_handle.get_lookback()

    def __len__(self):
        return len(self.__source_ds)

    def __call__(self, count=1, values_ago=0, include_none=True):
        ''' The same as self.getValues(), however this defaults to returning only
        the most recent value.
        '''
        return self.getValues(count, values_ago, include_none)

    def getValue(self, values_ago=0):
        ''' Returns the most recent values, or the specified number of bars previously.
        '''
        idx = len(self.__source_ds) - 1 - values_ago
        if idx < self.getWindowSize():
            return None
        return self.getValueAbsolute(idx)

    def getValues(self, count=None, values_ago=0, include_none=True):
        ''' Returns count (default = all) values sorted from oldest to newest, ending at values_ago.
        Raises IndexError if count is greater than the number of available values.
        '''
        if count == None:
            count = len(self)
        elif count <= 0:
            return None
        elif count > len(self.__source_ds) or (
            not include_none and count > ( len(self) - self.getWindowSize() )
        ):
            raise IndexError('count must be <= len(dataseries)')
        ret = OrderedDict()
        for k in self.__func_handle.get_output_names():
            ret[k] = []
        for i in xrange(count-1, -1, -1):
            value = self.getValue(i + values_ago)
            if value == None and include_none:
                for key in ret:
                    ret[key].append(None)
            else:
                for key in ret:
                    ret[key].append(value[key])
        return ret

    def getValueAbsolute(self, idx):
        ''' Returns the value at the absolute index idx. Absolute values are sorted
        from oldest to newest.
        Raises IndexError if idx is 
        '''
        if idx < 0 or idx > len(self.__source_ds)-1:
            raise IndexError
        elif idx < self.getWindowSize():
            return None

        if not self.__cache.initialized():
            self.__initialize_cache()
        elif self.__cache_dirty:
            self.__update_cache()

        try:
            value = self.__cache[idx]
        except IndexError:
            print 'cache index error'
            first_idx = idx - self.getWindowSize()
            assert(first_idx >= 0)
            value = self.calculateValue(first_idx, idx)
        return value

    def calculateValue(self, first_idx, last_idx):
        ''' If the value wasn't in the cache, we need to calculate new value(s).
        Retrieve the needed bars, call the function, and update the cache.
        Finally, return the requested value (ie last_idx).
        '''
        tmp_ds = dataseries.BarDataSeries()
        ds = self.getDataSeries()
        for i in xrange(first_idx, last_idx+1):
            tmp_ds.append(ds.getValueAbsolute(i))
        self.__func_handle.set_data_series(tmp_ds)
        data = self.__func_handle()
        self.__update_cache(data)
        return self.__cache[last_idx]
        
    def __initialize_cache(self):
        self.__func_handle.set_data_series(self.__cache_ds)
        if not self.__cache_ds:
            self.__func_handle.set_data_series(self.__source_ds)
        data = self.__func_handle()
        self.__cache.set_data(data)
        self.__cache_dirty = False

    def __update_cache(self, data=None):
        if data == None:
            data = self.__func_handle()
        self.__cache.append(data)
        self.__cache_dirty = False


class TA(object):
    ''' A unified interface for using TALIB functions with a BarFeed/Strategy.
    Note that this class only returns values for bars that have already been
    dispatched by the barfeed, and that under typical usage, the supplied
    barfeed will not have been started yet.
    '''
    def __init__(self, feed):
        self._feed = feed
        self._symbols = {}
        for symbol in self._feed.get_symbols():
            self._symbols[symbol] = {} # this inner dict holds the functions

    def get_functions(self):
        ret = []
        for functions in self.get_groups_of_functions().values():
            functions.sort()
            ret.extend(functions)
        return ret

    def get_groups_of_functions(self):
        ret = talib.get_function_groups()
        ret.pop('Math Operators')
        ret.pop('Math Transform')
        ret.pop('Statistic Functions')
        return ret

    def get(self, symbol, function):
        if symbol not in self._symbols:
            self._symbols[symbol] = {}
        if function not in self._symbols[symbol]:
            self._feed.start()
            while not self._feed.stopDispatching():
                self._feed.dispatch()
            cache_ds = self._feed.getDataSeries(symbol)
            self._feed.reset()
            ta_function = BarDataSeriesFilter(function, feed.getDataSeries(symbol), cache_ds)
            self._symbols[symbol][function] = ta_function
        return self._symbols[symbol][function]

    def print_help(self, function):
        self[function].print_help()

