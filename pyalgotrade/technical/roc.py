# PyAlgoTrade
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

from pyalgotrade import technical

class RateOfChange(technical.DataSeriesFilter):
	"""Rate of change filter as described in http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:rate_of_change.

	:param dataSeries: The DataSeries instance being filtered.
	:type dataSeries: :class:`pyalgotrade.dataseries.DataSeries`.
	:param values_ago: The number of values back that a given value will compare to. Must be > 0.
	:type values_ago: int.
	"""

	def __init__(self, dataSeries, values_ago):
		assert(values_ago > 0)
		technical.DataSeriesFilter.__init__(self, dataSeries, values_ago + 1)

	def calculateValue(self, first_idx, last_idx):
		prev = self.get_data_series().get_value_absolute(first_idx)
		actual = self.get_data_series().get_value_absolute(last_idx)

		if actual is None or prev is None or prev == 0:
			return None

		return (actual - prev) / float(prev) * 100

