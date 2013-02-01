# This file was originally part of PyAlgoTrade.
#
# Copyright 2012 Gabriel Martin Becedillas Ruiz
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

import numpy

# Returns the last values of a dataseries as a numpy.array, or None if not enough values could be retrieved from the dataseries.
def value_ds_to_numpy(ds, count):
    values = ds.get_values(count)
    if values == None:
        return None
    return numpy.array([float(value) for value in values])

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
