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
from pyalgotrade.technical import ma

class BarWrapper:
	def __init__(self, use_adjusted):
		self.__use_adjusted = use_adjusted

	def get_low(self, bar_):
		if self.__use_adjusted:
			return bar_.get_adj_low()
		else:
			return bar_.get_low()

	def get_high(self, bar_):
		if self.__use_adjusted:
			return bar_.get_adj_high()
		else:
			return bar_.get_high()

	def get_close(self, bar_):
		if self.__use_adjusted:
			return bar_.get_adj_close()
		else:
			return bar_.get_close()

def get_low_high_values(barWrapper, bars):
	currBar = bars[0]
	lowestLow = barWrapper.get_low(currBar)
	highestHigh = barWrapper.get_high(currBar)
	for i in range(len(bars)):
		currBar = bars[i]
		lowestLow = min(lowestLow, barWrapper.get_low(currBar))
		highestHigh = max(highestHigh, barWrapper.get_high(currBar))
	return (lowestLow, highestHigh)

class StochasticOscillator(technical.DataSeriesFilter):
	"""Stochastic Oscillator filter as described in http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:stochastic_oscillato.
	Note that the value returned by this filter is %K. To access %D use :meth:`getD`.

	:param bar_ds: The BarDataSeries instance being filtered.
	:type bar_ds: :class:`pyalgotrade.dataseries.BarDataSeries`.
	:param period: The period. Must be > 1.
	:type period: int.
	:param dSMAPeriod: The %D SMA period. Must be > 1.
	:type dSMAPeriod: int.
	:param use_adjustedValues: True to use adjusted Low/High/Close values.
	:type use_adjustedValues: boolean.
	"""

	def __init__(self, bar_ds, period, dSMAPeriod = 3, use_adjustedValues = False):
		assert(period > 1)
		assert(dSMAPeriod > 1)
		technical.DataSeriesFilter.__init__(self, bar_ds, period)
		self.__d = ma.SMA(self, dSMAPeriod)
		self.__barWrapper = BarWrapper(use_adjustedValues)

	def calculateValue(self, first_idx, last_idx):
		bars = self.get_data_series().get_values_absolute(first_idx, last_idx)
		if bars == None:
			return None

		lowestLow, highestHigh = get_low_high_values(self.__barWrapper, bars)
		currentClose = self.__barWrapper.get_close(bars[-1])
		return (currentClose - lowestLow) / float(highestHigh - lowestLow) * 100

	def getD(self):
		"""Returns a :class:`pyalgotrade.dataseries.DataSeries` with the %D values."""
		return self.__d

