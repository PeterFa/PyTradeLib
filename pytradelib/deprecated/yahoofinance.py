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

import urllib


def __adjust_month(month):
    if month > 12 or month < 1:
        raise Exception("Invalid month")
    month -= 1 # Month for yahoo is 0 based
    return month

def __get_last_day(month):
    ret = 31
    if month in (4, 6, 9, 11):
        ret = 30
    elif month == 2:
        ret = 28
    return ret

def __download_symbol_prices(symbol, from_month, from_year, to_month, to_year):
    from_day = 1
    to_day = __get_last_day(to_month)
    from_month = __adjust_month(from_month)
    to_month = __adjust_month(to_month)
    url = "http://ichart.finance.yahoo.com/table.csv?s=%s&a=%d&b=%d&c=%d&d=%d&e=%d&f=%d&g=d&ignore=.csv" % (symbol, from_month, from_day, from_year, to_month, to_day, to_year)

    f = urllib.urlopen(url)
    if f.headers['Content-Type'] != 'text/csv':
        raise Exception("Failed to download data")
    buff = f.read()

    # Remove the BOM
    while not buff[0].isalnum():
        buff = buff[1:]

    return buff

def get_daily_csv(symbol, year):
    from_month = 1
    to_month = 12
    return __download_symbol_prices(symbol, from_month, year, to_month, year)
