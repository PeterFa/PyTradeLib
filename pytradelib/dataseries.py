# This file was originally part of PyAlgoTrade.
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import bar


class DataSeries(object):
    """Base class for data series. A data series is an abstraction used to
    manage historical data.

        .. note::
            This is a base class and should not be used directly.
    """
    def __len__(self):
        """Returns the number of elements in the data series."""
        return self.get_length()

    def __getitem__(self, key):
        """Returns the value at a given position/slice. It raises IndexError if
        the position is invalid, or TypeError if the key type is invalid."""
        if isinstance(key, slice):
            return [self[i] for i in xrange(*key.indices(len(self)))]
        elif isinstance(key, int) :
            if key < 0:
                key += len(self)
            if key >= len(self) or key < 0:
                raise IndexError("Index out of range")
            return self.get_value_absolute(key)
        else:
            raise TypeError("Invalid argument type")

    def get_first_valid_index(self):
        raise Exception("Not implemented")

    def get_length(self):
        raise Exception("Not implemented")

    def get_value_absolute(self, pos):
        raise Exception("Not implemented")

    # Returns a sequence of absolute values [first_idx, last_idx]. If
    # include_none is False and *any* value is None, then None is returned.
    # TODO: Deprecate this.
    def get_values_absolute(self, first_idx, last_idx, include_none=False):
        ret = []
        for i in xrange(first_idx, last_idx+1):
            value = self.get_value_absolute(i)
            if value is None and not include_none:
                return None
            ret.append(value)
        return ret

    def __map_relative_to_absolute(self, values_ago):
        if values_ago < 0:
            return None

        ret = len(self) - values_ago - 1
        if ret < self.get_first_valid_index():
            ret = None
        return ret

    def get_values(self, count, values_ago=0, include_none=False):
        if count <= 0:
            return None

        absolute_idx = self.__map_relative_to_absolute(values_ago + (count - 1))
        if absolute_idx == None:
            return None

        ret = []
        for i in xrange(count):
            value = self.get_value_absolute(absolute_idx + i)
            if value is None and not include_none:
                return None
            ret.append(value)
        return ret

    # TODO: Deprecate this.
    def get_value(self, values_ago=0):
        ret = None
        absolute_idx = self.__map_relative_to_absolute(values_ago)
        if absolute_idx != None:
            ret = self.get_value_absolute(absolute_idx)
        return ret


class SequenceDataSeries(DataSeries):
    """A sequence based :class:`DataSeries`.

    :param values: The values that this DataSeries will hold. If values is None,
    an empty list is used. **Note that the list is not copied and the DataSeries
    takes ownership of it**.

    :type values: list.
    """
    def __init__(self, values=None):
        self.__idx = 0
        if values != None:
            self.__values = values
        else:
            self.__values = []

    def __len__(self):
        return len(self.__values)

    def __getitem__(self, key):
        return self.__values[key]

    def next(self):
        if self.__idx >= len(self.__values):
            self._reset_()
            raise StopIteration()
        ret = self.__values[self.__idx]
        self.__idx += 1
        return ret

    def __iter__(self):
        return self

    def _reset_(self):
        self.__idx = 0

    def get_first_valid_index(self):
        return 0

    def get_length(self):
        return len(self.__values)

    def get_value_absolute(self, pos):
        ret = None
        if pos >= 0 and pos < len(self.__values):
            ret = self.__values[pos]
        return ret

    def append_value(self, value):
        self.__values.append(value)


class BarValueDataSeries(DataSeries):
    def __init__(self, bar_ds, get_value_wrapper_func):
        self.__bar_ds = bar_ds
        self.__get_value_wrapper_func = get_value_wrapper_func

    def get_first_valid_index(self):
        return self.__bar_ds.get_first_valid_index()

    def get_length(self):
        return self.__bar_ds.get_length()

    def get_value_absolute(self, pos):
        ret = self.__bar_ds.get_value_absolute(pos)
        if ret != None:
            ret = self.__get_value_wrapper_func(ret)
        return ret

class BarDataSeries(SequenceDataSeries):
    """A :class:`DataSeries` of :class:`pytradelib.bar.Bar` instances."""
    def __init__(self):
        SequenceDataSeries.__init__(self)
        self.__last_date_time = None

    def append_value(self, value):
        # Check that bars are appended in order.
        assert(value != None)
        if self.__last_date_time != None \
          and value.get_date_time() <= self.__last_date_time:
            raise Exception("Appended datetime must be more recent than the previous ones.")
        self.__last_date_time = value.get_date_time()
        SequenceDataSeries.append_value(self, value)

    def get_open_data_series(self):
        """Returns a :class:`DataSeries` with the open prices."""
        return BarValueDataSeries(self, bar.Bar.get_open)

    def get_close_data_series(self):
        """Returns a :class:`DataSeries` with the close prices."""
        return BarValueDataSeries(self, bar.Bar.get_close)

    def get_high_data_series(self):
        """Returns a :class:`DataSeries` with the high prices."""
        return BarValueDataSeries(self, bar.Bar.get_high)

    def get_low_data_series(self):
        """Returns a :class:`DataSeries` with the low prices."""
        return BarValueDataSeries(self, bar.Bar.get_low)

    def get_volume_data_series(self):
        """Returns a :class:`DataSeries` with the volume."""
        return BarValueDataSeries(self, bar.Bar.get_volume)

    def get_adj_close_data_series(self):
        """Returns a :class:`DataSeries` with the adjusted close prices."""
        return BarValueDataSeries(self, bar.Bar.get_adj_close)
